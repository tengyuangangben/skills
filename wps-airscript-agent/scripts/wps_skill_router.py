import json
import os
import base64
import mimetypes
import sys
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


TOKEN_ENV = "WPS_AIRSCRIPT_TOKEN"
MAP_ENV = "WPS_WEBHOOK_MAP_PATH"


def _load_json_from_response(resp: requests.Response) -> Any:
    raw = resp.content or b""
    encodings: List[str] = []
    if getattr(resp, "encoding", None):
        encodings.append(str(resp.encoding))
    for enc in ("utf-8", "utf-8-sig", "gb18030", "cp936"):
        if enc not in encodings:
            encodings.append(enc)
    for enc in encodings:
        try:
            text = raw.decode(enc, errors="strict")
            return json.loads(text)
        except Exception:
            continue
    try:
        return resp.json()
    except Exception as e:
        sample = (raw[:300] or b"").decode("utf-8", errors="replace")
        raise ValueError(f"响应JSON解析失败: {e}; sample={sample}")
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


def _ensure_utf8_stdio() -> None:
    os.environ["PYTHONIOENCODING"] = "utf-8"
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


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


def _resolve_webhook_map_path() -> Path:
    env_path = str(os.getenv(MAP_ENV, "")).strip()
    if env_path:
        return Path(env_path).expanduser()
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent
    root_dir = script_dir.parent if script_dir.name.lower() == "scripts" else script_dir
    candidates: List[Path] = []
    for p in [
        script_path.with_name("wps_webhook_map.json"),
        root_dir / "wps_webhook_map.json",
        Path.cwd() / "wps_webhook_map.json"
    ]:
        if p not in candidates:
            candidates.append(p)
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def _resolve_submit_meta(submitter: str, submit_channel: str, user_data: Dict[str, Any], route: Dict[str, Any]) -> Tuple[str, str, str, str]:
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
        "OPENCLAW_CHANNEL", "OPENCLAW_CHAT_CHANNEL", "OPENCLAW_REQUEST_CHANNEL", "OPENCLAW_PLATFORM", "OPENCLAW_SOURCE_CHANNEL",
        "REQUESTER_GROUP_VALUE", "REQUEST_CHANNEL", "CONVERSATION_CHANNEL", "SOURCE_PLATFORM",
        "CHAT_CHANNEL", "CHAT_PLATFORM", "MESSAGE_CHANNEL", "MESSAGE_PLATFORM", "IM_PLATFORM", "SOURCE_CHANNEL",
        "CHANNEL", "PLATFORM", "CHANNEL_TYPE"
    ])
    route_default_channel = _first_non_empty(
        route.get("default_submit_channel"),
        route.get("default_channel")
    )
    fallback_channel = _first_non_empty(
        os.getenv("WPS_FALLBACK_SUBMIT_CHANNEL", ""),
        route_default_channel,
        "wecom"
    )
    if submitter:
        actual_submitter = submitter
        submitter_source = "arg"
    elif payload_submitter:
        actual_submitter = payload_submitter
        submitter_source = "payload"
    elif dynamic_submitter:
        actual_submitter = dynamic_submitter
        submitter_source = "runtime"
    elif os.getenv("WPS_SUBMITTER", ""):
        actual_submitter = str(os.getenv("WPS_SUBMITTER", "")).strip()
        submitter_source = "env_default"
    else:
        actual_submitter = "agent"
        submitter_source = "fallback_default"
    if submit_channel:
        actual_submit_channel = submit_channel
        submit_channel_source = "arg"
    elif dynamic_channel:
        actual_submit_channel = dynamic_channel
        submit_channel_source = "runtime"
    elif payload_channel:
        actual_submit_channel = payload_channel
        submit_channel_source = "payload"
    elif os.getenv("WPS_SUBMIT_CHANNEL", ""):
        actual_submit_channel = str(os.getenv("WPS_SUBMIT_CHANNEL", "")).strip()
        submit_channel_source = "env_default"
    else:
        actual_submit_channel = fallback_channel
        submit_channel_source = "fallback_default"
    return actual_submitter, actual_submit_channel, submitter_source, submit_channel_source


def load_webhook_map() -> Dict[str, Any]:
    map_path = _resolve_webhook_map_path()
    if not map_path.exists():
        script_path = Path(__file__).resolve()
        script_dir = script_path.parent
        root_dir = script_dir.parent if script_dir.name.lower() == "scripts" else script_dir
        tried = [
            str(script_path.with_name("wps_webhook_map.json")),
            str(root_dir / "wps_webhook_map.json"),
            str((Path.cwd() / "wps_webhook_map.json"))
        ]
        if os.getenv(MAP_ENV):
            tried.insert(0, str(Path(os.getenv(MAP_ENV, "")).expanduser()))
        raise ValueError(
            f"未找到 webhook 配置文件。请设置 {MAP_ENV} 或将 wps_webhook_map.json 放在技能目录。已尝试: {tried}"
        )
    with map_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _token_from_mapping(mapping: Dict[str, Any]) -> str:
    if not isinstance(mapping, dict):
        return ""
    for key in ("token", "wps_airscript_token", "airscript_token", "script_token", "airscriptToken"):
        val = mapping.get(key)
        if val and str(val).strip():
            return str(val).strip()
    cfg = mapping.get("config")
    if isinstance(cfg, dict):
        for key in ("token", "wps_airscript_token", "airscript_token", "script_token", "airscriptToken"):
            val = cfg.get(key)
            if val and str(val).strip():
                return str(val).strip()
    return ""


def get_token() -> str:
    token = ""
    try:
        token = _token_from_mapping(load_webhook_map())
    except Exception:
        token = ""
    if not token:
        token = os.getenv(TOKEN_ENV, "")
    if not token:
        raise ValueError(f"缺少脚本令牌，请在 wps_webhook_map.json 配置 token 或设置环境变量 {TOKEN_ENV}")
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
    return _compact_airscript_response(_load_json_from_response(resp))


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


def _pick_field_attr(obj: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for k in keys:
        if k in obj and obj.get(k) is not None:
            return obj.get(k)
    return default


def _bool_from_any(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "y", "是")


def _extract_select_options(items: Any) -> List[str]:
    out: List[str] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("Name") or item.get("text") or item.get("value") or "").strip()
            if name:
                out.append(name)
        else:
            text = str(item).strip()
            if text:
                out.append(text)
    return out


def _split_multi_select_value(v: Any) -> List[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    text = str(v or "").strip()
    if not text:
        return []
    for sep in ("|||", "、", ",", "，", "|", ";", "；", "\n"):
        if sep in text:
            return [x.strip() for x in text.split(sep) if x.strip()]
    return [text]


def _validate_user_data(field_config: List[Dict[str, Any]], user_data: Dict[str, Any], enforce_required: bool = True) -> None:
    cfg_by_name: Dict[str, Dict[str, Any]] = {}
    for cfg in field_config:
        name = str(_pick_field_attr(cfg, ["name", "Name"], "")).strip()
        if name:
            cfg_by_name[name] = cfg

    unknown_fields = [k for k in (user_data or {}).keys() if k not in cfg_by_name]
    if unknown_fields:
        raise ValueError(f"存在未识别字段: {unknown_fields}。请先用 fields 查看可用字段后重试。")

    for field_name, value in (user_data or {}).items():
        cfg = cfg_by_name.get(field_name, {})
        field_type = str(_pick_field_attr(cfg, ["type", "Type"], "")).strip()
        options = _extract_select_options(_pick_field_attr(cfg, ["items", "Items"], []))
        if field_type in ("SingleSelect", "单选") and options and str(value).strip():
            if str(value).strip() not in options:
                raise ValueError(f"字段[{field_name}]为单选，值[{value}]不在可选项中: {options}")
        if field_type in ("MultipleSelect", "多选") and options:
            values = _split_multi_select_value(value)
            invalid = [x for x in values if x not in options]
            if invalid:
                raise ValueError(f"字段[{field_name}]为多选，值{invalid}不在可选项中: {options}")

    if not enforce_required:
        return
    auto_types = {"CreateTime", "CreatedBy", "AutoNumber", "Formula", "Lookup"}
    missing_required: List[str] = []
    for cfg in field_config:
        name = str(_pick_field_attr(cfg, ["name", "Name"], "")).strip()
        if not name:
            continue
        required = _bool_from_any(_pick_field_attr(cfg, ["required", "Required"], False))
        field_type = str(_pick_field_attr(cfg, ["type", "Type"], "")).strip()
        if not required or field_type in auto_types:
            continue
        v = (user_data or {}).get(name)
        if v is None or str(v).strip() == "":
            missing_required.append(name)
    if missing_required:
        raise ValueError(f"缺少必填字段: {missing_required}")


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
    confirm_submit = _parse_bool(payload_data.pop("_confirm_submit", False), False) or _parse_bool(os.getenv("WPS_CONFIRM_SUBMIT", "false"), False)
    if _parse_bool(os.getenv("WPS_REQUIRE_CONFIRM_SUBMIT", "true"), True) and not confirm_submit:
        raise ValueError("未确认提交。请在用户明确“确认提交/提交/完成”后重试，或传入 _confirm_submit=true。")
    attachment_ocr_requested = _parse_bool(payload_data.pop("_allow_attachment_ocr", False), False) or _parse_bool(os.getenv("WPS_ALLOW_ATTACHMENT_OCR_REQUESTED", "false"), False)
    if _parse_bool(os.getenv("WPS_FORBID_ATTACHMENT_OCR_BY_DEFAULT", "true"), True) and (not attachment_ocr_requested) and _has_attachment_recognition_payload(payload_data):
        raise ValueError("检测到附件识别结果字段。默认禁止附件OCR内容写入；仅当用户明确要求时设置 _allow_attachment_ocr=true 或 WPS_ALLOW_ATTACHMENT_OCR_REQUESTED=true。")
    payload_allow_new_fields = _parse_bool(payload_data.pop("_allow_new_fields", False), False)
    payload_whitelist_raw = payload_data.pop("_new_fields_whitelist", [])
    payload_whitelist: List[str] = []
    if isinstance(payload_whitelist_raw, list):
        payload_whitelist = [str(x).strip() for x in payload_whitelist_raw if str(x).strip()]
    elif isinstance(payload_whitelist_raw, str):
        payload_whitelist = [x.strip() for x in payload_whitelist_raw.split(",") if x.strip()]
    env_allow_new_fields = _parse_bool(os.getenv("WPS_ALLOW_NEW_FIELDS", "false"), False)
    env_explicit_confirm = _parse_bool(os.getenv("WPS_ALLOW_NEW_FIELDS_REQUESTED", "false"), False)
    env_whitelist = [x.strip() for x in os.getenv("WPS_NEW_FIELDS_WHITELIST", "").split(",") if x.strip()]
    effective_whitelist = payload_whitelist or env_whitelist
    effective_allow_new_fields = env_allow_new_fields and (payload_allow_new_fields or env_explicit_confirm) and bool(effective_whitelist)
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
    _validate_user_data(field_config, payload_data, enforce_required=not overwrite_mode)
    fields = build_fields_payload(field_config, payload_data)
    if overwrite_mode and key_field and fields and isinstance(fields[0], list):
        one_record = fields[0]
        key_items = [x for x in one_record if isinstance(x, dict) and x.get("field_name") == key_field]
        if key_items:
            fields[0] = key_items + [x for x in one_record if not (isinstance(x, dict) and x.get("field_name") == key_field)]
    actual_submitter, actual_submit_channel, submitter_source, submit_channel_source = _resolve_submit_meta(submitter, submit_channel, payload_data, route)
    if _parse_bool(os.getenv("WPS_REQUIRE_SUBMIT_CHANNEL", "false"), False) and submit_channel_source in ("env_default", "fallback_default"):
        raise ValueError("缺少有效 submit_channel。请显式传入 submit_channel 或确保会话运行时渠道变量可用。")
    if _parse_bool(os.getenv("WPS_REQUIRE_SUBMITTER", "false"), False) and submitter_source in ("env_default", "fallback_default"):
        raise ValueError("缺少有效 submitter。请显式传入 submitter 或确保会话运行时用户变量可用。")
    argv = {
        "sheet_name": route.get("sheet_name"),
        "table_type": "多维表",
        "request_type": "content",
        "full_input_mode": False,
        "overwrite_mode": "是" if overwrite_mode else "否",
        "allow_new_fields": "是" if effective_allow_new_fields else "否",
        "new_fields_whitelist": effective_whitelist,
        "submitter": actual_submitter,
        "submit_channel": actual_submit_channel,
        "request_id": f"{route.get('key')}-{os.urandom(4).hex()}",
        "original_content": f"{intent}自动录入",
        "fields": fields
    }
    return post_airscript(write_webhook, argv, token)


def update_attachment_record(
    intent: str,
    key_field: str,
    key_value: Any,
    attachment_field: str,
    attachment_value: Any,
    merge_mode: str = "replace"
) -> Dict[str, Any]:
    if not key_field:
        raise ValueError("缺少 WPS_UPDATE_KEY_FIELD")
    if key_value in (None, ""):
        raise ValueError("缺少 WPS_UPDATE_KEY_VALUE")
    if not attachment_field:
        raise ValueError("缺少 WPS_UPDATE_ATTACHMENT_FIELD")
    mode = str(merge_mode or "replace").strip().lower()
    patch_value: Any = attachment_value
    if mode in ("append", "merge", "追加", "合并"):
        q = query_records_enhanced(
            intent=intent,
            monitor_field_name=key_field,
            monitor_content=str(key_value),
            check_field_rule="等于",
            return_mode="selected_fields",
            return_fields=[attachment_field],
            include_attachment_fields=True
        )
        _, rows = _extract_result_rows(q)
        existing_value: Any = None
        if rows and isinstance(rows[0], dict):
            existing_value = rows[0].get(attachment_field)
        patch_value = _merge_attachment_values(existing_value, attachment_value)
    patch_data: Dict[str, Any] = {
        attachment_field: patch_value
    }
    return create_record(intent, patch_data, overwrite_mode=True, key_field=key_field, key_value=key_value)


def update_record_fields(
    intent: str,
    key_field: str,
    key_value: Any,
    update_data: Dict[str, Any],
    must_exist: bool = True
) -> Dict[str, Any]:
    if not key_field:
        raise ValueError("缺少 WPS_UPDATE_KEY_FIELD")
    if key_value in (None, ""):
        raise ValueError("缺少 WPS_UPDATE_KEY_VALUE")
    patch = dict(update_data or {})
    if not patch:
        raise ValueError("缺少 WPS_UPDATE_FIELDS_JSON")
    if key_field in patch:
        patch.pop(key_field, None)
    if not patch:
        raise ValueError("更新字段不能为空")
    if must_exist:
        q = query_records_enhanced(
            intent=intent,
            monitor_field_name=key_field,
            monitor_content=str(key_value),
            check_field_rule="等于",
            return_mode="selected_fields",
            return_fields=[key_field],
            include_attachment_fields=False
        )
        _, rows = _extract_result_rows(q)
        if not rows:
            raise ValueError(f"未找到待更新记录: {key_field}={key_value}")
    return create_record(intent, patch, overwrite_mode=True, key_field=key_field, key_value=key_value)


def delete_records(
    intent: str,
    delete_field_name: str = "",
    delete_field_value: str = "",
    delete_field_rule: str = "等于",
    query_conditions: Optional[List[Dict[str, Any]]] = None,
    request_id: str = "",
    record_ids: Optional[List[str]] = None,
    max_delete_count: int = 200
) -> Dict[str, Any]:
    mapping = load_webhook_map()
    token = get_token()
    route = find_route(intent, mapping)
    delete_webhook = route.get("delete_webhook", "")
    if not delete_webhook or "请替换" in str(delete_webhook):
        raise ValueError(f"{route.get('name')} 未配置 delete_webhook")
    ids = [str(x).strip() for x in (record_ids or []) if str(x).strip()]
    rule = str(delete_field_rule or "等于").strip()
    field_name = str(delete_field_name or "").strip()
    field_value = "" if delete_field_value is None else str(delete_field_value)
    if rule == "等于" and field_name and field_value.strip() == "":
        rule = "为空"
    field_condition_ready = bool(field_name) and (field_value.strip() != "" or rule in ("为空", "不为空"))
    if not ids and not request_id and not field_condition_ready:
        raise ValueError("删除需要提供 record_ids，或 request_id，或有效字段条件（含 为空/不为空）")
    argv: Dict[str, Any] = {
        "sheet_name": route.get("sheet_name"),
        "table_type": "多维表",
        "request_type": "delete_record",
        "delete_field_name": field_name,
        "delete_field_value": field_value,
        "delete_field_rule": rule,
        "query_conditions": query_conditions or [],
        "request_id": request_id,
        "request_id_field_name": route.get("request_id_field_name", "_请求ID"),
        "record_ids": ids,
        "max_delete_count": max(1, int(max_delete_count))
    }
    return post_airscript(delete_webhook, argv, token)


def get_required_fields(intent: str) -> Dict[str, Any]:
    def pick(obj: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
        for k in keys:
            if k in obj and obj.get(k) is not None:
                return obj.get(k)
        return default

    def bool_from(v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "y", "是")

    def extract_options(v: Any) -> List[str]:
        out: List[str] = []
        if not isinstance(v, list):
            return out
        for item in v:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("Name") or item.get("text") or item.get("value") or "").strip()
                if name:
                    out.append(name)
            else:
                text = str(item).strip()
                if text:
                    out.append(text)
        return out

    def field_view(f: Dict[str, Any]) -> Dict[str, Any]:
        name = str(pick(f, ["name", "Name"], "")).strip()
        field_type = str(pick(f, ["type", "Type"], "")).strip()
        field_format = TYPE_TO_FORMAT.get(field_type, "文本")
        required = bool_from(pick(f, ["required", "Required"], False))
        is_primary = bool_from(pick(f, ["isPrimary", "IsPrimary"], False))
        options = extract_options(pick(f, ["items", "Items"], []))
        desc_parts: List[str] = []
        if field_type in ("CreateTime", "CreatedBy", "AutoNumber", "Formula", "Lookup"):
            desc_parts.append("自动生成")
        if is_primary:
            desc_parts.append("唯一")
        if required:
            desc_parts.append("必填")
        if options:
            desc_parts.append(" / ".join(options))
        return {
            "name": name,
            "type": field_type,
            "format": field_format,
            "required": required,
            "is_primary": is_primary,
            "options": options,
            "description": "；".join(desc_parts)
        }

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
        "fields": [field_view(f) for f in field_config]
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


def _attachment_items_from_value(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    def append_item(data: Dict[str, str]) -> None:
        if isinstance(data, dict) and data:
            items.append(data)

    if isinstance(value, list):
        for x in value:
            items.extend(_attachment_items_from_value(x))
        return items

    if isinstance(value, dict):
        if isinstance(value.get("files"), list):
            for x in value.get("files", []):
                items.extend(_attachment_items_from_value(x))
            return items
        file_name = str(value.get("file_name") or value.get("name") or value.get("fileName") or value.get("title") or "").strip()
        file_url = str(value.get("file_url") or value.get("url") or value.get("link") or value.get("download_url") or value.get("href") or "").strip()
        file_path = str(value.get("file_path") or value.get("path") or "").strip()
        file_data = str(value.get("file_data") or value.get("file_base64") or value.get("base64") or value.get("data_uri") or value.get("dataUri") or "").strip()
        if file_url:
            append_item({"file_url": file_url, "file_name": file_name})
            return items
        if file_path:
            append_item({"file_path": file_path, "file_name": file_name})
            return items
        if file_data:
            append_item({"file_data": file_data, "file_name": file_name})
            return items
        return items

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return items
        if text.lower().startswith("http://") or text.lower().startswith("https://"):
            append_item({"file_url": text})
        elif text.lower().startswith("data:"):
            append_item({"file_data": text})
        else:
            append_item({"file_path": text})
    return items


def _attachment_signature(item: Dict[str, str]) -> str:
    if item.get("file_url"):
        return f"url|{item.get('file_url')}|{item.get('file_name', '')}"
    if item.get("file_path"):
        return f"path|{item.get('file_path')}|{item.get('file_name', '')}"
    data = item.get("file_data", "")
    if data:
        digest = hashlib.sha1(data.encode("utf-8", errors="ignore")).hexdigest()
        return f"data|{digest}|{item.get('file_name', '')}"
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def _merge_attachment_values(existing_value: Any, new_value: Any) -> Dict[str, Any]:
    merged: List[Dict[str, str]] = []
    seen: set[str] = set()
    for src in (_attachment_items_from_value(existing_value), _attachment_items_from_value(new_value)):
        for item in src:
            sig = _attachment_signature(item)
            if sig in seen:
                continue
            seen.add(sig)
            merged.append(item)
    return {"files": merged}


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


def _has_attachment_recognition_payload(obj: Any) -> bool:
    suspicious_keys = {
        "ocr_text", "ocr", "recognized_text", "parsed_text", "extract_text", "extracted_text",
        "summary", "analysis", "content_text", "text_content"
    }
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).strip().lower()
            if key in suspicious_keys:
                return True
            if _has_attachment_recognition_payload(v):
                return True
        return False
    if isinstance(obj, list):
        return any(_has_attachment_recognition_payload(x) for x in obj)
    return False


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
    map_path = _resolve_webhook_map_path()
    mapping = load_webhook_map()
    token_from_map = _token_from_mapping(mapping)
    token_from_env = os.getenv(TOKEN_ENV, "")
    token = token_from_map or token_from_env
    token_source = "map" if token_from_map else ("env" if token_from_env else "")
    routes = []
    for route in mapping.get("routes", []):
        routes.append({
            "key": route.get("key"),
            "name": route.get("name"),
            "sheet_name": route.get("sheet_name"),
            "write_webhook_configured": bool(route.get("write_webhook")) and "请替换" not in str(route.get("write_webhook")),
            "query_webhook_configured": bool(route.get("query_webhook")) and "请替换" not in str(route.get("query_webhook")),
            "field_query_webhook_configured": bool(route.get("field_query_webhook")) and "请替换" not in str(route.get("field_query_webhook")),
            "delete_webhook_configured": bool(route.get("delete_webhook")) and "请替换" not in str(route.get("delete_webhook"))
        })
    return {
        "token_configured": bool(token),
        "token_env": TOKEN_ENV,
        "token_source": token_source,
        "map_path": str(map_path),
        "map_exists": map_path.exists(),
        "routes": routes
    }


if __name__ == "__main__":
    _ensure_utf8_stdio()
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
            merge_mode = os.getenv("WPS_UPDATE_ATTACHMENT_MODE", "replace")
            print(json.dumps(update_attachment_record(demo_intent, key_field, key_value, attachment_field, attachment_value, merge_mode), ensure_ascii=False, indent=2))
        elif mode == "update":
            key_field = os.getenv("WPS_UPDATE_KEY_FIELD", "")
            key_value = os.getenv("WPS_UPDATE_KEY_VALUE", "")
            update_data = json.loads(os.getenv("WPS_UPDATE_FIELDS_JSON", "{}"))
            must_exist = _parse_bool(os.getenv("WPS_UPDATE_MUST_EXIST", "true"), True)
            print(json.dumps(update_record_fields(demo_intent, key_field, key_value, update_data, must_exist), ensure_ascii=False, indent=2))
        elif mode == "delete":
            delete_field_name = os.getenv("WPS_DELETE_FIELD", "")
            delete_field_value = os.getenv("WPS_DELETE_VALUE", "")
            delete_field_rule = os.getenv("WPS_DELETE_RULE", "等于")
            query_conditions = json.loads(os.getenv("WPS_DELETE_CONDITIONS_JSON", "[]"))
            request_id = os.getenv("WPS_DELETE_REQUEST_ID", "")
            record_ids = json.loads(os.getenv("WPS_DELETE_RECORD_IDS_JSON", "[]"))
            max_delete_count = int(os.getenv("WPS_DELETE_MAX_COUNT", "200") or "200")
            print(json.dumps(delete_records(demo_intent, delete_field_name, delete_field_value, delete_field_rule, query_conditions, request_id, record_ids, max_delete_count), ensure_ascii=False, indent=2))
        else:
            demo_data = json.loads(os.getenv("WPS_SKILL_DATA", "{}"))
            overwrite_mode = _parse_bool(os.getenv("WPS_OVERWRITE_MODE", "false"), False)
            key_field = os.getenv("WPS_KEY_FIELD", "")
            key_value = os.getenv("WPS_KEY_VALUE", "")
            print(json.dumps(create_record(demo_intent, demo_data, overwrite_mode=overwrite_mode, key_field=key_field, key_value=key_value), ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"state": "error", "message": str(e)}, ensure_ascii=False, indent=2))
