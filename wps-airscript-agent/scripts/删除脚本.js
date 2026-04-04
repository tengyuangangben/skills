const shtType = Application.FileInfo.officeType
const table_type = Context.argv.table_type || "多维表"
const shtName = Context.argv.sheet_name
const request_type = Context.argv.request_type || "delete_record"
const delete_field_name = Context.argv.delete_field_name || ""
const delete_field_value = Context.argv.delete_field_value || ""
const delete_field_rule = Context.argv.delete_field_rule || "等于"
const query_conditions = Array.isArray(Context.argv.query_conditions) ? Context.argv.query_conditions : []
const request_id = Context.argv.request_id || ""
const request_id_field_name = Context.argv.request_id_field_name || "_请求ID"
const max_delete_count = parseInt(Context.argv.max_delete_count || 200, 10) || 200
const record_ids = Array.isArray(Context.argv.record_ids) ? Context.argv.record_ids.map(x => normalizeRecordId(x)).filter(Boolean) : []

if (request_type != "delete_record") {
  return { "respData": { "state": "error" }, "msg": "仅支持 delete_record", "deleted_count": 0, "deleted_ids": [] }
}

let sht = shtType != "d" ? Application.Sheets(shtName) : getShtWithName(shtName)
if (!sht) {
  return { "respData": { "state": "error" }, "msg": `未找到数据表: ${shtName}`, "deleted_count": 0, "deleted_ids": [] }
}
if (shtType != "d") sht.Activate()

let deleteIds = []
if (record_ids.length > 0) {
  deleteIds = record_ids.slice(0, max_delete_count)
} else {
  const recs = getAllRecords(sht)
  const filtered = recs.filter(rec => matchRecord(rec))
  deleteIds = filtered.map(rec => normalizeRecordId(rec && (rec.id != null ? rec.id : (rec.Id != null ? rec.Id : rec.recordId)))).filter(Boolean).slice(0, max_delete_count)
}

if (deleteIds.length == 0) {
  return { "respData": { "state": "success" }, "msg": "未匹配到可删除记录", "deleted_count": 0, "deleted_ids": [] }
}

const deleted = (shtType == "k" ? sht : Application).Record.DeleteRecords({
  SheetId: sht.id ? sht.id : sht.Id,
  RecordIds: deleteIds
})

return {
  "respData": { "state": "success" },
  "msg": "删除成功",
  "deleted_count": Array.isArray(deleted) ? deleted.length : deleteIds.length,
  "deleted_ids": deleteIds
}

function getAllRecords(shtObj) {
  let all = []
  let offset = null
  while (all.length === 0 || offset) {
    let records = (shtType == "k" ? shtObj : Application).Record.GetRecords({
      SheetId: shtObj.id ? shtObj.id : shtObj.Id,
      Offset: offset,
      TextValue: "compound"
    })
    offset = records.offset
    all = all.concat(records.records || [])
  }
  return all
}

function recordTextValue(rec, field) {
  if (!rec || !rec.fields || !field) return ""
  let fv = rec.fields[field]
  if (fv == null) return ""
  if (typeof fv == "string" || typeof fv == "number" || typeof fv == "boolean") return String(fv)
  if (typeof fv == "object") {
    if (fv.text != null) return String(fv.text)
    if (Array.isArray(fv.options)) return fv.options.map(x => String(x)).join("|||")
    if (Array.isArray(fv.files)) return fv.files.map(x => x.name || x.file_name || "").join("|||")
  }
  return String(fv)
}

function matchRecord(rec) {
  if (request_id) {
    const reqVal = recordTextValue(rec, request_id_field_name)
    if (reqVal != request_id) return false
  }
  if (delete_field_name) {
    const val = recordTextValue(rec, delete_field_name)
    if (!matchRule(val, delete_field_value, delete_field_rule)) return false
  }
  for (let i = 0; i < query_conditions.length; i++) {
    const cond = query_conditions[i] || {}
    const field = cond.field || ""
    if (!field) continue
    const val = recordTextValue(rec, field)
    if (!matchCondition(val, cond)) return false
  }
  return request_id || delete_field_name || query_conditions.length > 0
}

function matchRule(value, target, rule) {
  const v = String(value || "")
  const t = String(target || "")
  switch (rule) {
    case "等于": return v === t
    case "不等于": return v !== t
    case "包含": return v.indexOf(t) >= 0
    case "不包含": return v.indexOf(t) < 0
    case "开头是": return v.startsWith(t)
    case "结尾是": return v.endsWith(t)
    case "为空": return v.trim() === ""
    case "不为空": return v.trim() !== ""
    case "大于": return toNum(v) > toNum(t)
    case "大于等于": return toNum(v) >= toNum(t)
    case "小于": return toNum(v) < toNum(t)
    case "小于等于": return toNum(v) <= toNum(t)
    default: return v === t
  }
}

function matchCondition(value, cond) {
  const op = String(cond.op || "").toLowerCase()
  const target = cond.value
  if (op == "contains" || op == "包含") return String(value).indexOf(String(target)) >= 0
  if (op == "not_contains" || op == "不包含") return String(value).indexOf(String(target)) < 0
  if (op == "gt" || op == "大于") return toNum(value) > toNum(target)
  if (op == "gte" || op == "大于等于") return toNum(value) >= toNum(target)
  if (op == "lt" || op == "小于") return toNum(value) < toNum(target)
  if (op == "lte" || op == "小于等于") return toNum(value) <= toNum(target)
  if (op == "between" || op == "范围") return toNum(cond.min) <= toNum(value) && toNum(value) <= toNum(cond.max)
  if (op == "equals" || op == "eq" || op == "等于") return String(value) == String(target)
  return true
}

function toNum(v) {
  return parseFloat(String(v || "").replace(/,/g, "").trim())
}

function getShtWithName(name) {
  let sheet
  const sheets = Application.Sheets
  for (let i = 0; i < sheets.Count; i++) {
    const temp = sheets.Item(i + 1)
    if (temp.Name == name) {
      sheet = temp
      break
    }
  }
  return sheet
}

function normalizeRecordId(v) {
  if (v == null) return ""
  if (typeof v == "string" || typeof v == "number" || typeof v == "boolean") return String(v).trim()
  if (typeof v == "object") {
    const cand = v.id != null ? v.id : (v.Id != null ? v.Id : (v.recordId != null ? v.recordId : (v.value != null ? v.value : (v.text != null ? v.text : ""))))
    return cand == null ? "" : String(cand).trim()
  }
  return String(v).trim()
}
