import json
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_MAP_PATH = Path(__file__).with_name("wps_webhook_map.json")


def ask(prompt: str, default: str = "", required: bool = False) -> str:
    while True:
        text = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
        if text:
            return text
        if default:
            return default
        if not required:
            return ""
        print("该项必填，请重新输入。")


def ask_yes_no(prompt: str, default_yes: bool = True) -> bool:
    default = "Y/n" if default_yes else "y/N"
    while True:
        text = input(f"{prompt} ({default}): ").strip().lower()
        if not text:
            return default_yes
        if text in ("y", "yes"):
            return True
        if text in ("n", "no"):
            return False
        print("请输入 y 或 n。")


def load_map(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"token": "", "routes": []}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"token": "", "routes": []}
    if not isinstance(data.get("routes"), list):
        data["routes"] = []
    if "token" not in data:
        data["token"] = ""
    return data


def save_map(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def input_route(existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    base = existing or {}
    key = ask("路由key", str(base.get("key", "")), required=True)
    name = ask("业务名称", str(base.get("name", "")), required=True)
    sheet_name = ask("表名称(sheet_name)", str(base.get("sheet_name", "")), required=True)
    aliases_text = ask("别名（逗号分隔）", ",".join(base.get("aliases", [])))
    aliases = [x.strip() for x in aliases_text.split(",") if x.strip()]
    write_webhook = ask("录入脚本write_webhook", str(base.get("write_webhook", "")), required=True)
    delete_webhook = ask("删除脚本delete_webhook", str(base.get("delete_webhook", "")))
    query_webhook = ask("查询脚本query_webhook", str(base.get("query_webhook", "")), required=True)
    field_query_webhook = ask("字段查询脚本field_query_webhook", str(base.get("field_query_webhook", "")), required=True)
    request_id_field_name = ask("请求ID字段名(request_id_field_name)", str(base.get("request_id_field_name", "_请求ID")) or "_请求ID")
    default_notification_mode = ask("默认通知模式", str(base.get("default_notification_mode", "text")) or "text")
    default_range_mode = ask("默认范围模式", str(base.get("default_range_mode", "all")) or "all")
    range_cfg = base.get("range_filter_fields", {}) if isinstance(base.get("range_filter_fields"), dict) else {}
    user_field_name = ask("范围用户字段名(user_field_name)", str(range_cfg.get("user_field_name", "")))
    group_field_name = ask("范围分组字段名(group_field_name)", str(range_cfg.get("group_field_name", "")))
    field_query_args_text = ask("字段查询附加参数JSON(field_query_args)", json.dumps(base.get("field_query_args", {}), ensure_ascii=False))
    try:
        field_query_args = json.loads(field_query_args_text) if field_query_args_text else {}
        if not isinstance(field_query_args, dict):
            field_query_args = {}
    except Exception:
        field_query_args = {}
    return {
        "key": key,
        "name": name,
        "sheet_name": sheet_name,
        "aliases": aliases,
        "write_webhook": write_webhook,
        "delete_webhook": delete_webhook,
        "query_webhook": query_webhook,
        "field_query_webhook": field_query_webhook,
        "request_id_field_name": request_id_field_name,
        "field_query_args": field_query_args,
        "default_notification_mode": default_notification_mode,
        "default_range_mode": default_range_mode,
        "range_filter_fields": {
            "user_field_name": user_field_name,
            "group_field_name": group_field_name
        }
    }


def upsert_route(routes: List[Dict[str, Any]], route: Dict[str, Any]) -> None:
    key = route.get("key")
    for i, item in enumerate(routes):
        if item.get("key") == key:
            routes[i] = route
            return
    routes.append(route)


def main() -> None:
    map_path = Path(ask("路由配置文件路径", str(DEFAULT_MAP_PATH), required=True))
    data = load_map(map_path)
    token = ask("脚本令牌token（可留空走环境变量）", str(data.get("token", "")))
    data["token"] = token
    routes = data.get("routes", [])
    print(f"当前路由数量: {len(routes)}")
    if routes:
        for item in routes:
            print(f"- {item.get('key')} | {item.get('name')} | {item.get('sheet_name')}")
    while True:
        action = ask("操作类型(add/edit/done)", "add").lower()
        if action == "done":
            break
        if action not in ("add", "edit"):
            print("仅支持 add/edit/done")
            continue
        existing = None
        if action == "edit":
            target_key = ask("请输入要编辑的路由key", required=True)
            for item in routes:
                if item.get("key") == target_key:
                    existing = item
                    break
            if not existing:
                print("未找到该key，将按新增处理。")
        route = input_route(existing)
        upsert_route(routes, route)
        print(f"已保存路由: {route.get('key')}")
        if not ask_yes_no("继续配置下一条路由？", default_yes=True):
            break
    data["routes"] = routes
    save_map(map_path, data)
    print("路由配置写入完成。")
    print(f"文件路径: {map_path}")
    print("下一步：")
    print("1) 若未配置map中的token，则设置环境变量 WPS_AIRSCRIPT_TOKEN")
    print("2) 执行: python wps_skill_router.py (WPS_SKILL_MODE=setup)")


if __name__ == "__main__":
    main()
