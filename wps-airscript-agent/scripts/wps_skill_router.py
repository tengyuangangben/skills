import json
import os
import base64
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


TOKEN_ENV = "WPS_AIRSCRIPT_TOKEN"
MAP_ENV = "WPS_WEBHOOK_MAP_PATH"
DEFAULT_MAP_PATH = Path(__file__).with_name("wps_webhook_map.json")


TYPE_TO_FORMAT = {
    "MultiLineText": "文本",
    "SingleLineText": "文本",
    "Date": "文本",
    "Time": "文本",
    "Number": "数字",
    "Currency": "数字",
    "Percentage": "数字",
    "ID": "文本",
    "Phone": "文本",
    "Email": "文本",
    "Url": "文本",
    "Checkbox": "文本",
    "SingleSelect": "文本",
    "MultipleSelect": "文本",
    "Rating": "数字",
    "Complete": "数字",
    "Contact": "文本",
    "Attachment": "附件",
    "Link": "文本",
    "Note": "文本",
    "AutoNumber": "文本",
    "CreatedBy": "文本",
    "CreateTime": "文本",
    "Formula": "文本",
    "Lookup": "文本"
}


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "y", "是"):
        return True
    if s in ("0", "false", "no", "n", "否"):
        return False
    return default


def _compact_airscript_response(data: Dict[str, Any]) -> Dict[str, Any]:
    if _env_bool("WPS_KEEP_AIRSCRIPT_LOGS", False):
        return data
    if not isinstance(data, dict):
        return data
    payload = data.get("data")
    if isinstance(payload, dict) and "logs" in payload:
        payload = dict(payload)
        payload.pop("logs", None)
        out = dict(data)
        out["data"] = payload
        return out
    return data


def _first_non_empty(*values: Any) -> str:
    for v in values:
        if v is None:
            continue
        text = str(v).strip()
        if text:
            return text
    return ""


def _env_first(names: List[str]) -> str:
    for name in names:
        v = os.getenv(name, "")
        if v and str(v).strip():
            return str(v).strip()
    return ""


def _resolve_submit_meta(submitter: str, submit_channel: str, user_data: Dict[str, Any], route: Dict[str, Any]) -> Tuple[str, str]:
    payload = user_data or {}
    payload_submitter = _first_non_empty(
        payload.get("submitter"),
        payload.get("_提交人"),
        payload.get("提交人"),
        payload.get("nickname"),
        payload.get("user_name"),
        payload.get("username")
    )
    payload_channel = _first_non_empty(
        payload.get("submit_channel"),
        payload.get("_提交渠道"),
        payload.get("提交渠道"),
        payload.get("channel"),
        payload.get("source_channel"),
        payload.get("platform")
    )
    dynamic_submitter = _env_first([
        "OPENCLAW_SUBMITTER", "OPENCLAW_USER", "OPENCLAW_USERNAME", "OPENCLAW_NICKNAME",
        "REQUESTER_USER_VALUE", "CHAT_USER", "CHAT_USERNAME", "MESSAGE_USER", "SENDER_NAME", "SENDER_ID"
    ])
    dynamic_channel = _env_first([
        "OPENCLAW_CHANNEL", "OPENCLAW_PLATFORM", "REQUESTER_GROUP_VALUE",
        "CHAT_CHANNEL", "CHAT_PLATFORM", "MESSAGE_CHANNEL", "MESSAGE_PLATFORM", "IM_PLATFORM", "SOURCE_CHANNEL"
    ])
    actual_submitter = _first_non_empty(
        submitter,
        payload_submitter,
        dynamic_submitter,
        os.getenv("WPS_SUBMITTER", ""),
        "agent"
    )
    actual_submit_channel = _first_non_empty(
        submit_channel,
        payload_channel,
        dynamic_channel,
        os.getenv("WPS_SUBMIT_CHANNEL", ""),
        route.get("key")
    )
    return actual_submitter, actual_submit_channel


def load_webhook_map() -> Dict[str, Any]:
    map_path = Path(os.getenv(MAP_ENV, str(DEFAULT_MAP_PATH)))
    with map_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_token() -> str:
    token = os.getenv(TOKEN_ENV, "")
    if not token:
        raise ValueError(f"缺少环境变量 {TOKEN_ENV}")
    return token


def find_route(intent: str, mapping: Dict[str, Any]) -> Dict[str, Any]:
    lowered = intent.strip().lower()
    for route in mapping.get("routes", []):
        aliases = [str(a).strip().lower() for a in route.get("aliases", [])]
        name = str(route.get("name", "")).strip().lower()
        key = str(route.get("key", "")).strip().lower()
        if lowered in aliases or lowered == name or lowered == key:
            return route
        for alias in aliases:
            if alias and alias in lowered:
                return route
    raise ValueError(f"未匹配到业务路由: {intent}")


def post_airscript(webhook: str, argv: Dict[str, Any], token: str) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json", "AirScript-Token": token}
    payload = {"Context": {"argv": argv}}
    resp = requests.post(webhook, json=payload, headers=headers, timeout=30)
    if resp.status_code >= 400:
        detail = resp.text[:500] if resp.text else ""
        raise ValueError(f"调用失败 status={resp.status_code} webhook={webhook} detail={detail}")
    return _compact_airscript_response(resp.json())


def get_fields_config(route: Dict[str, Any], token: str) -> List[Dict[str, Any]]:
    webhook = route.get("field_query_webhook", "")
    if not webhook or "请替换" in webhook:
        raise ValueError(f"{route.get('name')} 未配置 field_query_webhook")
    argv = {
        "sheet_name": route.get("sheet_name"),
        "include_raw": True
    }
    extra_query_args = route.get("field_query_args", {})
    if isinstance(extra_query_args, dict):
        argv.update(extra_query_args)
    result = post_airscript(webhook, argv, token)
    resp_data = ((result or {}).get("respData")) or {}
    if not resp_data:
        resp_data = ((((result or {}).get("data") or {}).get("result") or {}).get("respData") or {})
    fields = (resp_data.get("fields")) or []
    fields = [f for f in fields if isinstance(f, dict) and (f.get("name") or f.get("Name") or f.get("type") or f.get("Type"))]
    if not fields:
        raw_fields = (resp_data.get("raw_fields")) or []
        fields = [f for f in raw_fields if isinstance(f, dict) and (f.get("name") or f.get("Name") or f.get("type") or f.get("Type"))]
    if not fields:
        raise ValueError(f"{route.get('name')} 未返回字段配置")
    return fields


def build_fields_payload(field_config: List[Dict[str, Any]], user_data: Dict[str, Any]) -> List[List[Dict[str, Any]]]:
    def get_field_name(cfg: Dict[str, Any]) -> str:
        return str(cfg.get("name") or cfg.get("Name") or "")

    def get_field_type(cfg: Dict[str, Any]) -> str:
        return str(cfg.get("type") or cfg.get("Type") or "MultiLineText")

    def file_to_data_uri(file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"附件文件不存在: {file_path}")
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "application/octet-stream"
        data = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{data}"

    def parse_mime_from_data_uri(data_uri: str) -> str:
        if not data_uri.lower().startswith("data:"):
            return "application/octet-stream"
        head = data_uri.split(",", 1)[0]
        mime = head[5:].split(";", 1)[0].strip()
        return mime or "application/octet-stream"

    def ensure_data_uri(raw_data: str, file_name: str = "") -> str:
        text = raw_data.strip()
        if text.lower().startswith("data:"):
            return text
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = "application/octet-stream"
        return f"data:{mime_type};base64,{text}"

    def filename_from_data_uri(data_uri: str, fallback: str) -> str:
        mime = parse_mime_from_data_uri(data_uri)
        ext = mimetypes.guess_extension(mime) or ""
        name = (fallback or "附件").strip()
        if "." not in Path(name).name and ext:
            return f"{name}{ext}"
        return name

    def download_url_to_data_uri(url: str) -> tuple[str, str]:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        mime_type = resp.headers.get("Content-Type", "").split(";", 1)[0].strip() or "application/octet-stream"
        file_name = Path(url.split("?", 1)[0]).name or "附件"
        data = base64.b64encode(resp.content).decode("utf-8")
        return f"data:{mime_type};base64,{data}", file_name

    def normalize_attachment_input(value: Any) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []

        def append_item(kind: str, payload: str, file_name: str = "") -> None:
            if payload:
                out.append({"kind": kind, "payload": payload, "file_name": file_name})

        if isinstance(value, str):
            text = value.strip()
            if text.lower().startswith("http://") or text.lower().startswith("https://"):
                append_item("url", text, "")
            elif text.lower().startswith("data:"):
                append_item("data", text, "")
            else:
                append_item("path", text, "")
            return out

        if isinstance(value, dict):
            if isinstance(value.get("files"), list):
                for item in value.get("files", []):
                    out.extend(normalize_attachment_input(item))
                return out
            file_name = str(value.get("file_name", "")).strip()
            if value.get("file_data"):
                append_item("data", str(value.get("file_data")), file_name)
            elif value.get("file_base64"):
                append_item("data", str(value.get("file_base64")), file_name)
            elif value.get("file_url"):
                append_item("url", str(value.get("file_url")), file_name)
            elif value.get("file_path"):
                append_item("path", str(value.get("file_path")), file_name)
            elif value.get("file_paths") and isinstance(value.get("file_paths"), list):
                for p in value.get("file_paths", []):
                    append_item("path", str(p), "")
            return out

        if isinstance(value, list):
            for item in value:
                out.extend(normalize_attachment_input(item))
            return out
        return out

    one_record: List[Dict[str, Any]] = []
    config_by_name = {get_field_name(item): item for item in field_config if get_field_name(item)}
    for field_name, value in user_data.items():
        cfg = config_by_name.get(field_name, {})
        field_type = get_field_type(cfg)
        field_format = TYPE_TO_FORMAT.get(field_type, "文本")
        item: Dict[str, Any] = {
            "field_name": field_name,
            "value": value,
            "field_format": field_format
        }
        if field_format == "附件":
            attachments = normalize_attachment_input(value)
            if attachments:
                file_data_list: List[str] = []
                file_name_list: List[str] = []
                for idx, item_data in enumerate(attachments):
                    kind = item_data.get("kind", "")
                    payload = item_data.get("payload", "").strip()
                    hint_name = item_data.get("file_name", "").strip()
                    if not payload:
                        continue
                    if kind == "path":
                        path = Path(payload)
                        file_data = file_to_data_uri(payload)
                        file_name = hint_name or path.name
                    elif kind == "url":
                        file_data, url_name = download_url_to_data_uri(payload)
                        file_name = hint_name or url_name
                    else:
                        file_data = ensure_data_uri(payload, hint_name)
                        file_name = hint_name or filename_from_data_uri(file_data, f"附件{idx + 1}")
                    file_data_list.append(file_data)
                    file_name_list.append(file_name)
                item["value"] = ""
                item["file_base64"] = "|||".join(file_data_list)
                item["file_name"] = "|||".join(file_name_list)
        one_record.append(item)
    return [one_record]


def create_record(
    intent: str,
    user_data: Dict[str, Any],
    submitter: str = "",
    submit_channel: str = "",
    overwrite_mode: bool = False,
    key_field: str = "",
    key_value: Any = None
) -> Dict[str, Any]:
    mapping = load_webhook_map()
    token = get_token()
    route = find_route(intent, mapping)
    write_webhook = route.get("write_webhook", "")
    if not write_webhook or "请替换" in write_webhook:
        raise ValueError(f"{route.get('name')} 未配置 write_webhook")
    payload_data: Dict[str, Any] = dict(user_data or {})
    if overwrite_mode and key_field:
        if key_value not in (None, ""):
            payload_data[key_field] = key_value
        if key_field in payload_data:
            ordered_data: Dict[str, Any] = {key_field: payload_data[key_field]}
            for k, v in payload_data.items():
                if k != key_field:
                    ordered_data[k] = v
            payload_data = ordered_data
    field_config = get_fields_config(route, token)
    fields = build_fields_payload(field_config, payload_data)
    actual_submitter, actual_submit_channel = _resolve_submit_meta(submitter, submit_channel, payload_data, route)
    argv = {
        "sheet_name": route.get("sheet_name"),
        "table_type": "多维表",
        "request_type": "content",
        "full_input_mode": False,
        "overwrite_mode": "是" if overwrite_mode else "否",
        "allow_new_fields": "是" if _parse_bool(os.getenv("WPS_ALLOW_NEW_FIELDS", "false"), False) else "否",
        "new_fields_whitelist": [x.strip() for x in os.getenv("WPS_NEW_FIELDS_WHITELIST", "").split(",") if x.strip()],
        "submitter": actual_submitter,
        "submit_channel": actual_submit_channel,
        "request_id": f"{route.get('key')}-{os.urandom(4).hex()}",
        "original_content": f"{intent}自动录入",
        "fields": fields
    }
    return post_airscript(write_webhook, argv, token)


def update_attachment_record(intent: str, key_field: str, key_value: Any, attachment_field: str, attachment_value: Any) -> Dict[str, Any]:
    if not key_field:
        raise ValueError("缺少 WPS_UPDATE_KEY_FIELD")
    if key_value in (None, ""):
        raise ValueError("缺少 WPS_UPDATE_KEY_VALUE")
    if not attachment_field:
        raise ValueError("缺少 WPS_UPDATE_ATTACHMENT_FIELD")
    patch_data: Dict[str, Any] = {
        attachment_field: attachment_value
    }
    return create_record(intent, patch_data, overwrite_mode=True, key_field=key_field, key_value=key_value)


def get_required_fields(intent: str) -> Dict[str, Any]:
    mapping = load_webhook_map()
    token = get_token()
    route = find_route(intent, mapping)
    field_config = get_fields_config(route, token)
    return {
        "intent": intent,
        "route": route.get("key"),
        "sheet_name": route.get("sheet_name"),
        "recommended_range_mode": route.get("default_range_mode", "all"),
        "range_filter_fields": route.get("range_filter_fields", {}),
        "fields": [{"name": f.get("name"), "type": f.get("type")} for f in field_config]
    }


def build_query_argv(
    intent: str,
    monitor_field_name: str,
    monitor_content: str,
    requester_user_value: str = "",
    requester_group_value: str = "",
    notification_field_name: str = "",
    range_mode: str = "",
    check_field_rule: str = "等于",
    return_mode: str = "notification",
    return_fields: Optional[List[str]] = None,
    query_conditions: Optional[List[Dict[str, Any]]] = None,
    aggregate: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    mapping = load_webhook_map()
    route = find_route(intent, mapping)
    notification_mode = route.get("default_notification_mode", "text")
    actual_notification_field_name = notification_field_name or monitor_field_name
    actual_range_mode = range_mode or route.get("default_range_mode", "all")
    return {
        "table_name": route.get("sheet_name"),
        "table_type": "多维表",
        "monitor_field_name": monitor_field_name,
        "monitor_content": monitor_content,
        "check_field_rule": check_field_rule,
        "notification_field_name": actual_notification_field_name,
        "notification_type": "文本" if notification_mode == "text" else notification_mode,
        "notification_mode": notification_mode,
        "data_range": 20,
        "range_mode": actual_range_mode,
        "range_filter_fields": route.get("range_filter_fields", {}),
        "requester_user_value": requester_user_value,
        "requester_group_value": requester_group_value,
        "return_mode": return_mode,
        "return_fields": return_fields or [],
        "query_conditions": query_conditions or [],
        "aggregate": aggregate or {}
    }


def query_records(
    intent: str,
    monitor_field_name: str,
    monitor_content: str,
    requester_user_value: str = "",
    requester_group_value: str = "",
    notification_field_name: str = "",
    range_mode: str = "",
    check_field_rule: str = "等于",
    return_mode: str = "notification",
    return_fields: Optional[List[str]] = None,
    query_conditions: Optional[List[Dict[str, Any]]] = None,
    aggregate: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    mapping = load_webhook_map()
    token = get_token()
    route = find_route(intent, mapping)
    query_webhook = route.get("query_webhook", "")
    if not query_webhook or "请替换" in query_webhook:
        raise ValueError(f"{route.get('name')} 未配置 query_webhook")
    argv = build_query_argv(
        intent, monitor_field_name, monitor_content,
        requester_user_value, requester_group_value,
        notification_field_name, range_mode, check_field_rule,
        return_mode, return_fields, query_conditions, aggregate
    )
    return post_airscript(query_webhook, argv, token)


def _extract_result_rows(result: Dict[str, Any]) -> Tuple[List[Any], List[Any]]:
    body = ((result or {}).get("data") or {}).get("result") or {}
    ids = body.get("ids") or []
    rows = body.get("respData") or []
    if not isinstance(ids, list):
        ids = []
    if not isinstance(rows, list):
        rows = []
    return ids, rows


def _extract_result_body(result: Dict[str, Any]) -> Dict[str, Any]:
    return ((result or {}).get("data") or {}).get("result") or {}


def _to_num(v: Any) -> float:
    text = str(v).replace(",", "").strip()
    return float(text)


def _parse_bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "y", "是"):
        return True
    if s in ("0", "false", "no", "n", "否"):
        return False
    return default


def _match_condition(value: Any, cond: Dict[str, Any]) -> bool:
    op = str(cond.get("op", "")).lower()
    target = cond.get("value")
    if op in ("contains", "包含"):
        return str(target) in str(value)
    if op in ("not_contains", "不包含"):
        return str(target) not in str(value)
    if op in ("gt", "大于"):
        return _to_num(value) > _to_num(target)
    if op in ("gte", "大于等于"):
        return _to_num(value) >= _to_num(target)
    if op in ("lt", "小于"):
        return _to_num(value) < _to_num(target)
    if op in ("lte", "小于等于"):
        return _to_num(value) <= _to_num(target)
    if op in ("between", "范围"):
        return _to_num(cond.get("min")) <= _to_num(value) <= _to_num(cond.get("max"))
    return True


def _apply_conditions_local(rows: List[Dict[str, Any]], query_conditions: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not query_conditions:
        return rows
    out: List[Dict[str, Any]] = []
    for row in rows:
        ok = True
        for cond in query_conditions:
            field = cond.get("field")
            if not field:
                continue
            if not _match_condition(row.get(field, ""), cond):
                ok = False
                break
        if ok:
            out.append(row)
    return out


def _aggregate_rows(rows: List[Dict[str, Any]], aggregate: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not aggregate:
        return {}
    op = str(aggregate.get("op", "")).lower()
    field = aggregate.get("field")
    if op in ("count", "计数"):
        return {"op": "count", "value": len(rows)}
    if not field:
        return {}
    nums: List[float] = []
    for row in rows:
        try:
            nums.append(_to_num(row.get(field, "")))
        except Exception:
            pass
    if not nums:
        return {"op": op, "field": field, "value": None}
    if op in ("sum", "求和", "total"):
        return {"op": "sum", "field": field, "value": sum(nums)}
    if op in ("avg", "average", "平均"):
        return {"op": "avg", "field": field, "value": sum(nums) / len(nums)}
    if op in ("min", "最小"):
        return {"op": "min", "field": field, "value": min(nums)}
    if op in ("max", "最大"):
        return {"op": "max", "field": field, "value": max(nums)}
    return {}


def query_records_enhanced(
    intent: str,
    monitor_field_name: str,
    monitor_content: str,
    requester_user_value: str = "",
    requester_group_value: str = "",
    notification_field_name: str = "",
    range_mode: str = "",
    check_field_rule: str = "等于",
    return_mode: str = "notification",
    return_fields: Optional[List[str]] = None,
    query_conditions: Optional[List[Dict[str, Any]]] = None,
    aggregate: Optional[Dict[str, Any]] = None,
    include_attachment_fields: bool = False
) -> Dict[str, Any]:
    if return_mode == "notification" and not return_fields and not query_conditions and not aggregate:
        return query_records(intent, monitor_field_name, monitor_content, requester_user_value, requester_group_value, notification_field_name, range_mode, check_field_rule, return_mode, return_fields, query_conditions, aggregate)
    direct_result = query_records(
        intent, monitor_field_name, monitor_content,
        requester_user_value, requester_group_value,
        notification_field_name, range_mode, check_field_rule,
        return_mode, return_fields, query_conditions, aggregate
    )
    direct_body = _extract_result_body(direct_result)
    direct_rows = direct_body.get("respData")
    direct_ids = direct_body.get("ids")
    if isinstance(direct_rows, list) and isinstance(direct_ids, list):
        if return_mode == "all_fields" and not include_attachment_fields and direct_rows:
            token = get_token()
            mapping = load_webhook_map()
            route = find_route(intent, mapping)
            fields_cfg = get_fields_config(route, token)
            attachment_names = {
                str(item.get("name") or item.get("Name"))
                for item in fields_cfg
                if str(item.get("type") or item.get("Type") or "") == "Attachment" and (item.get("name") or item.get("Name"))
            }
            if attachment_names:
                cleaned_rows: List[Dict[str, Any]] = []
                for row in direct_rows:
                    if isinstance(row, dict):
                        cleaned_rows.append({k: v for k, v in row.items() if k not in attachment_names})
                    else:
                        cleaned_rows.append(row)
                direct_rows = cleaned_rows
        totalcount = direct_body.get("totalcount")
        if not isinstance(totalcount, int):
            totalcount = len(direct_rows)
        agg = direct_body.get("aggregate")
        if not isinstance(agg, dict):
            agg = {}
        if aggregate and not agg:
            rows_for_agg = [r for r in direct_rows if isinstance(r, dict)]
            agg = _aggregate_rows(rows_for_agg, aggregate)
        return {
            "status": "finished",
            "error": "",
            "data": {
                "result": {
                    "ids": direct_ids,
                    "respData": direct_rows,
                    "totalcount": totalcount,
                    "aggregate": agg
                }
            }
        }

    token = get_token()
    mapping = load_webhook_map()
    route = find_route(intent, mapping)
    fields: List[str] = []
    if return_mode == "all_fields":
        fields_cfg = get_fields_config(route, token)
        filtered_cfg = fields_cfg
        if not include_attachment_fields:
            filtered_cfg = [item for item in fields_cfg if str(item.get("type") or item.get("Type") or "") != "Attachment"]
        fields = [str(item.get("name") or item.get("Name")) for item in filtered_cfg if (item.get("name") or item.get("Name"))]
    elif return_fields:
        fields = return_fields
    else:
        fields = [notification_field_name or monitor_field_name]
    merged: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for f in fields:
        result = query_records(intent, monitor_field_name, monitor_content, requester_user_value, requester_group_value, f, range_mode, check_field_rule, "notification", None, None, None)
        ids, rows = _extract_result_rows(result)
        for idx, rid in enumerate(ids):
            rid = str(rid)
            if rid not in merged:
                merged[rid] = {}
                order.append(rid)
            row = rows[idx] if idx < len(rows) and isinstance(rows[idx], dict) else {}
            if f in row:
                merged[rid][f] = row[f]
    records_with_ids = [(rid, merged[rid]) for rid in order]
    if query_conditions:
        filtered: List[Tuple[str, Dict[str, Any]]] = []
        for rid, row in records_with_ids:
            matched = _apply_conditions_local([row], query_conditions)
            if matched:
                filtered.append((rid, row))
        records_with_ids = filtered
    final_ids = [rid for rid, _ in records_with_ids]
    records = [row for _, row in records_with_ids]
    agg_result = _aggregate_rows(records, aggregate)
    return {
        "status": "finished",
        "error": "",
        "data": {
            "result": {
                "ids": final_ids,
                "respData": records,
                "totalcount": len(records),
                "aggregate": agg_result
            }
        }
    }


def format_query_result_for_human(result: Dict[str, Any]) -> str:
    body = (((result or {}).get("data") or {}).get("result") or {})
    resp = body.get("respData")
    aggregate = body.get("aggregate") or {}
    if (not isinstance(resp, list) or not resp) and not aggregate:
        return "未查询到数据"
    lines: List[str] = []
    if isinstance(resp, list):
        for idx, record in enumerate(resp, 1):
            lines.append(f"记录{idx}：")
            if isinstance(record, dict):
                for k, v in record.items():
                    lines.append(f"{k}：{v}")
            else:
                lines.append(f"内容：{record}")
    if aggregate:
        lines.append("汇总：")
        for k, v in aggregate.items():
            lines.append(f"{k}：{v}")
    return "\n".join(lines)


def get_setup_status() -> Dict[str, Any]:
    mapping = load_webhook_map()
    token = os.getenv(TOKEN_ENV, "")
    routes = []
    for route in mapping.get("routes", []):
        routes.append({
            "key": route.get("key"),
            "name": route.get("name"),
            "sheet_name": route.get("sheet_name"),
            "write_webhook_configured": bool(route.get("write_webhook")) and "请替换" not in str(route.get("write_webhook")),
            "query_webhook_configured": bool(route.get("query_webhook")) and "请替换" not in str(route.get("query_webhook")),
            "field_query_webhook_configured": bool(route.get("field_query_webhook")) and "请替换" not in str(route.get("field_query_webhook"))
        })
    return {
        "token_configured": bool(token),
        "token_env": TOKEN_ENV,
        "map_path": os.getenv(MAP_ENV, str(DEFAULT_MAP_PATH)),
        "routes": routes
    }


if __name__ == "__main__":
    try:
        demo_intent = os.getenv("WPS_SKILL_INTENT", "报销")
        mode = os.getenv("WPS_SKILL_MODE", "fields")
        if mode == "setup":
            print(json.dumps(get_setup_status(), ensure_ascii=False, indent=2))
        elif mode == "fields":
            print(json.dumps(get_required_fields(demo_intent), ensure_ascii=False, indent=2))
        elif mode == "query_argv":
            monitor_field_name = os.getenv("WPS_QUERY_MONITOR_FIELD", "状态")
            monitor_content = os.getenv("WPS_QUERY_MONITOR_CONTENT", "待处理")
            requester_user_value = os.getenv("WPS_QUERY_USER", "")
            requester_group_value = os.getenv("WPS_QUERY_GROUP", "")
            notification_field_name = os.getenv("WPS_QUERY_NOTIFICATION_FIELD", "")
            range_mode = os.getenv("WPS_QUERY_RANGE_MODE", "")
            check_field_rule = os.getenv("WPS_QUERY_RULE", "等于")
            return_mode = os.getenv("WPS_QUERY_RETURN_MODE", "notification")
            return_fields = [x.strip() for x in os.getenv("WPS_QUERY_RETURN_FIELDS", "").split(",") if x.strip()]
            query_conditions = json.loads(os.getenv("WPS_QUERY_CONDITIONS_JSON", "[]"))
            aggregate = json.loads(os.getenv("WPS_QUERY_AGG_JSON", "{}"))
            print(json.dumps(build_query_argv(demo_intent, monitor_field_name, monitor_content, requester_user_value, requester_group_value, notification_field_name, range_mode, check_field_rule, return_mode, return_fields, query_conditions, aggregate), ensure_ascii=False, indent=2))
        elif mode == "query":
            monitor_field_name = os.getenv("WPS_QUERY_MONITOR_FIELD", "状态")
            monitor_content = os.getenv("WPS_QUERY_MONITOR_CONTENT", "待处理")
            requester_user_value = os.getenv("WPS_QUERY_USER", "")
            requester_group_value = os.getenv("WPS_QUERY_GROUP", "")
            notification_field_name = os.getenv("WPS_QUERY_NOTIFICATION_FIELD", "")
            range_mode = os.getenv("WPS_QUERY_RANGE_MODE", "")
            check_field_rule = os.getenv("WPS_QUERY_RULE", "等于")
            return_mode = os.getenv("WPS_QUERY_RETURN_MODE", "notification")
            return_fields = [x.strip() for x in os.getenv("WPS_QUERY_RETURN_FIELDS", "").split(",") if x.strip()]
            query_conditions = json.loads(os.getenv("WPS_QUERY_CONDITIONS_JSON", "[]"))
            aggregate = json.loads(os.getenv("WPS_QUERY_AGG_JSON", "{}"))
            include_attachment_fields = _parse_bool(os.getenv("WPS_QUERY_INCLUDE_ATTACHMENTS", "false"), False)
            output_format = os.getenv("WPS_QUERY_OUTPUT_FORMAT", "json")
            result = query_records_enhanced(demo_intent, monitor_field_name, monitor_content, requester_user_value, requester_group_value, notification_field_name, range_mode, check_field_rule, return_mode, return_fields, query_conditions, aggregate, include_attachment_fields)
            if output_format == "text":
                print(format_query_result_for_human(result))
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        elif mode == "update_attachment":
            key_field = os.getenv("WPS_UPDATE_KEY_FIELD", "")
            key_value = os.getenv("WPS_UPDATE_KEY_VALUE", "")
            attachment_field = os.getenv("WPS_UPDATE_ATTACHMENT_FIELD", "")
            attachment_value = json.loads(os.getenv("WPS_UPDATE_ATTACHMENT", "{}"))
            print(json.dumps(update_attachment_record(demo_intent, key_field, key_value, attachment_field, attachment_value), ensure_ascii=False, indent=2))
        else:
            demo_data = json.loads(os.getenv("WPS_SKILL_DATA", "{}"))
            overwrite_mode = _parse_bool(os.getenv("WPS_OVERWRITE_MODE", "false"), False)
            key_field = os.getenv("WPS_KEY_FIELD", "")
            key_value = os.getenv("WPS_KEY_VALUE", "")
            print(json.dumps(create_record(demo_intent, demo_data, overwrite_mode=overwrite_mode, key_field=key_field, key_value=key_value), ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"state": "error", "message": str(e)}, ensure_ascii=False, indent=2))
