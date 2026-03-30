const shtType = Application.FileInfo.officeType;


let shtName
let viewName
let viewId
let monitor_field_name
let monitor_content
let monitor_field_rule
let notification_field_name
let notification_type
let notification_mode
let return_mode
let return_fields
let query_conditions
let text_notification_field
let watermark_field
let data_range
let data_range_condition
let range_mode
let wechat_id
let chatroom_id
let range_filter_fields

let file_notification_text_field
let dashboard_title
let dashboard_description
let dashboard_thumb
let table_type
let title_row_index
let filterFields = []
table_type = Context.argv.table_type
title_row_index = Context.argv.title_row_index
shtName = Context.argv.table_name;
viewName = Context.argv.view_name;
data_range = Context.argv.data_range
data_range_condition = Context.argv.data_range_condition
range_mode = Context.argv.range_mode
range_filter_fields = normalizeRangeFilterFields(Context.argv.range_filter_fields)
wechat_id = Context.argv.requester_user_value || Context.argv.wechat_id
chatroom_id = Context.argv.requester_group_value || Context.argv.chatroom_id

dashboard_description = Context.argv.dashboard_description
dashboard_title = Context.argv.dashboard_title
dashboard_thumb = Context.argv.dashboard_thumb_link
const sht = shtType != "d" ? Application.Sheets(shtName) : getShtWithName(shtName);
if (shtType != "d") {
  sht.Activate()
}
monitor_field_name = Context.argv.monitor_field_name; //查询字段名字
monitor_content = Context.argv.monitor_content;//查询内容
monitor_field_rule = Context.argv.check_field_rule;

op = translateRule(monitor_field_rule)
notification_field_name = Context.argv.notification_field_name; //通知字段名称
notification_type = Context.argv.notification_type;//通知字段类型
notification_mode = Context.argv.notification_mode
return_mode = Context.argv.return_mode || "notification"
return_fields = normalizeReturnFields(Context.argv.return_fields)
query_conditions = normalizeQueryConditions(Context.argv.query_conditions)
text_notification_field = Context.argv.text_notification_field; //图片类型通知字段时，文本通知字段名称
watermark_field = Context.argv.watermark_field; //水印通知字段
file_notification_text_field = Context.argv.file_notification_text_field

filterFields = [notification_field_name, monitor_field_name, ...return_fields]
let notify_fieldtype = "";  //表内通知字段类型
const rangeMode = getRangeMode(range_mode || data_range_condition)
const normalizedNotificationMode = getNotificationMode(notification_mode || notification_type)

// try {

let fld = getFieldWithName(sht, notification_field_name);
if (!fld) {
  fld = createFiled(sht, notification_field_name);
}
notify_fieldtype = fld.type
if (return_mode == "all_fields") {
  const allFieldNames = getAllFieldNames(sht)
  for (let i = 0; i < allFieldNames.length; i++) {
    pushUnique(filterFields, allFieldNames[i])
  }
}

if (rangeMode != "all") {
  if (rangeMode == "user" || rangeMode == "both") {
    fld = getFieldWithName(sht, range_filter_fields.user_field_name)
    if (!fld) {
      fld = createFiled(sht, range_filter_fields.user_field_name)
    }
    pushUnique(filterFields, range_filter_fields.user_field_name)
  }
  if (rangeMode == "group" || rangeMode == "both") {
    fld = getFieldWithName(sht, range_filter_fields.group_field_name)
    if (!fld) {
      fld = createFiled(sht, range_filter_fields.group_field_name)
    }
    pushUnique(filterFields, range_filter_fields.group_field_name)
  }
}

if (normalizedNotificationMode == "image") {
  if (watermark_field != "") {
    fld = getFieldWithName(sht, watermark_field);
    if (!fld) {
      createFiled(sht, watermark_field);
    }
    filterFields.push(watermark_field)
  }
  if (text_notification_field != "") {

    fld = getFieldWithName(sht, text_notification_field);
    if (!fld) {
      createFiled(sht, text_notification_field);
    }
    filterFields.push(text_notification_field)
  }
} else if (normalizedNotificationMode == "file") {
  if (file_notification_text_field != "") {
    fld = getFieldWithName(sht, file_notification_text_field);
    if (!fld) {
      createFiled(sht, file_notification_text_field);
    }
    filterFields.push(file_notification_text_field)
  }
} else if (normalizedNotificationMode == "dashboard_link") {
  if (dashboard_title != "") {
    fld = getFieldWithName(sht, dashboard_title);
    if (!fld) {
      createFiled(sht, dashboard_title);
    }
    filterFields.push(dashboard_title)
  }
  if (dashboard_description != "") {

    fld = getFieldWithName(sht, dashboard_description);
    if (!fld) {
      createFiled(sht, dashboard_description);
    }
    filterFields.push(dashboard_description)
  }
  if (dashboard_thumb != "") {

    fld = getFieldWithName(sht, dashboard_thumb);
    if (!fld) {
      createFiled(sht, dashboard_thumb);
    }
    filterFields.push(dashboard_thumb)
  }
}
filterFields = Array.from(new Set(filterFields.filter(item => item != undefined && item !== "")))

viewId = shtType != "d" ? viewId : getVieWIdWithName(sht, viewName)
if (table_type != "在线工作表") {
  let criterias = []
  if (rangeMode != "all") {
    switch (rangeMode) {
      case "group":
        criterias.push({
          "field": range_filter_fields.group_field_name,
          "op": "Contains",
          "values": [chatroom_id]
        }
        )
        break
      case "user":
        criterias.push({
          "field": range_filter_fields.user_field_name,
          "op": "Contains",
          "values": [wechat_id]
        }
        )
        break
      case "both":
        criterias.push({
          "field": range_filter_fields.user_field_name,
          "op": "Contains",
          "values": [wechat_id]
        }
        )
        criterias.push({
          "field": range_filter_fields.group_field_name,
          "op": "Contains",
          "values": [chatroom_id]
        }
        )
        break
    }
  }

  let recs = Array.from(getAllRecordsWithFilter(sht, viewId, filterFields, op, criterias));
  
  if (monitor_field_rule == "被包含") {
    recs = recs.filter(item => {
      if(!item)return false
      let fld = item.fields[monitor_field_name] || {};
      let value = fld.text || "";
      return monitor_content.indexOf(value) > -1;
    });
  } else if (monitor_field_rule == "不被包含") {
    recs = recs.filter(item => {
      if(!item)return false
      let fld = item.fields[monitor_field_name] || {};
      let value = fld.text || "";
      return monitor_content.indexOf(value) == -1;
    });
  } else if (monitor_field_rule == "正则表达式") {
    recs = recs.filter(item => {
      if(!item)return false
      let fld = item.fields[monitor_field_name] || {};
      let value = fld.text || "";
      return isMatch(monitor_content, value,"s")
    });
  }
  recs = applyQueryConditions(recs, query_conditions, true)

  let tableData = [];
  let ids = [];
  let updateRecs = [];
  let updateRecsNone = [];//通知内容空的
  let updated = [];
  let totalcount = 0 //实际查询数量
  if (recs[0]) {
    totalcount = recs.length
    if (data_range >= 0) {
      recs = recs.slice(0, data_range)
    } else {
      recs = recs.slice(data_range)
    }

    Array.from(recs).forEach((item, index) => {

      itemfield = {}
      if (return_mode != "notification") {
        itemfield = buildRecordOutput(item, true, return_mode, return_fields)
        tableData.push(itemfield)
        ids.push(item.id)
        return
      }
      let notifyValue = item.fields[notification_field_name]
      let nvalue = notifyValue ? notifyValue.value : ""
      let ntext = notifyValue ? notifyValue.text : ""
      if (normalizedNotificationMode == "text") {

        itemfield[notification_field_name] = ntext


      } else if (normalizedNotificationMode == "dashboard_link") {
        itemfield[notification_field_name] = ntext
        if (dashboard_title != "") {

          itemfield[dashboard_title] = item.fields[dashboard_title] ? item.fields[dashboard_title].text : ""

        }
        if (dashboard_description != "") {
          itemfield[dashboard_description] = item.fields[dashboard_description] ? item.fields[dashboard_description].text : ""
        }
        if (dashboard_thumb != "") {
          itemfield[dashboard_thumb] = item.fields[dashboard_thumb] ? item.fields[dashboard_thumb].text : ""
        }
      } else if (normalizedNotificationMode == "image") {

        itemfield[notification_field_name] = (notify_fieldtype == "Attachment" || notify_fieldtype == "Lookup") ? getImageUrls(nvalue) : ntext
        if (watermark_field != "") {

          itemfield[watermark_field] = item.fields[watermark_field] ? item.fields[watermark_field].text : ""

        }
        if (text_notification_field != "") {
          itemfield[text_notification_field] = item.fields[text_notification_field] ? item.fields[text_notification_field].text : ""
        }
      } else if (normalizedNotificationMode == "file") {

        if (file_notification_text_field != "") {
          itemfield[file_notification_text_field] = item.fields[file_notification_text_field] ? item.fields[file_notification_text_field].text : ""
        }
        itemfield[notification_field_name] = (notify_fieldtype == "Attachment" || notify_fieldtype == "Lookup") ? getFileUrls(nvalue) : ntext

      } else {
        itemfield[notification_field_name] = ntext
      }

      tableData.push(itemfield)
      ids.push(item.id)

    })



  }
  if (tableData.length > 0) {
    return { "respData": tableData, "ids": ids, "totalcount": totalcount };
  } else {


    return { "respData": "未查询到数据，请重试" }
  }

  // } catch (e) {
  //   console.log({ "respData": "出错" & JSON.stringify(e) })
  //   return { "respData": "出错" & JSON.stringify(e) }
  // }

} else { //在线工作表
  sht.Activate()
  let recs = Array.from(getAllRecordsFromTableSheet1(sht, filterFields, monitor_field_rule))
  if (monitor_field_rule == "被包含") {
    recs = recs.filter(item => {
      let fld = item.fields[monitor_field_name] || {};
      let value = fld || "";
      return monitor_content.indexOf(value) > -1;
    });
  } else if (monitor_field_rule == "不被包含") {
    recs = recs.filter(item => {
      let fld = item.fields[monitor_field_name] || {};
      let value = fld || "";
      return monitor_content.indexOf(value) == -1;
    });
  } else if (monitor_field_rule == "正则表达式") {
    recs = recs.filter(item => {
      let fld = item.fields[monitor_field_name] || {};
      let value = fld || "";
      return isMatch(monitor_content, value,"s")
    });
  }
  recs = applyQueryConditions(recs, query_conditions, false)

  let tableData = [];
  let ids = [];
  let updateRecs = [];
  let updateRecsNone = [];//通知内容空的
  let updated = [];
  let totalcount = 0 //实际查询数量
  if (recs[0]) {
    totalcount = recs.length
    if (data_range >= 0) {
      recs = recs.slice(0, data_range)
    } else {
      recs = recs.slice(data_range)
    }

    Array.from(recs).forEach((item, index) => {

      itemfield = {}
      if (return_mode != "notification") {
        itemfield = buildRecordOutput(item, false, return_mode, return_fields)
        tableData.push(itemfield)
        ids.push(item.id)
        return
      }
      let notifyValue = item.fields[notification_field_name]

      if (normalizedNotificationMode == "text") {

        itemfield[notification_field_name] = notifyValue


      } else if (normalizedNotificationMode == "image") {

        sht.Activate()
        sht.LoadAllData()
        sht.Cells(item.id, item.n_cid).Select()

        let imgUrl = sht.Shapes.GetActiveShapeImg() || ""
        if (imgUrl != "") imgUrl = [imgUrl]
        console.log("imgurl" + imgUrl)
        itemfield[notification_field_name] = imgUrl
        if (watermark_field != "") {

          itemfield[watermark_field] = item.fields[watermark_field]

        }
        if (text_notification_field != "") {
          itemfield[text_notification_field] = item.fields[text_notification_field]
        }
      } else {
        itemfield[notification_field_name] = notifyValue
      }

      tableData.push(itemfield)
      ids.push(item.id)

    })



  }
  console.log("tableData", tableData)
  if (tableData.length > 0) {

    return { "respData": tableData, "ids": ids, "totalcount": totalcount };
  } else {


    return { "respData": "未查询到数据，请重试" }
  }
}




/* 以下封装函数 */

function translateRule(rule) {
  switch (rule) {
    case '等于':
      return 'Equals';
    case '不等于':
      return 'NotEqu';
    case '开头是':
      return 'BeginWith';
    case '结尾是':
      return 'EndWith';
    case '包含':
      return 'Contains';
    case '不包含':
      return 'NotContains';
    case '为空':
      return 'Empty';
    case '不为空':
      return 'NotEmpty';
    case '被包含':
      return 'BeContains';
    case '不被包含':
      return 'NotBeContains';
    case '正则表达式':
      return 'regex'
    default:
      return 'Equals';
  }
}
function getImageUrls(fieldValue) {
  fieldValue = flattenArray(fieldValue)

  let imageUrlsArr = []
  for (let i = 0; i < fieldValue.length; i++) {
    if (fieldValue[i].type.includes("image") || fieldValue[i].imgSize) {
      let val = (shtType == "k" ? sht : Application).Record.GetAttachmentURL({
        UploadId: fieldValue[i].uploadId,
        Source: fieldValue[i].source
      });
      if (val) {
        imageUrlsArr.push(val)
      }

    }
  }
  return imageUrlsArr

}


function isTypeAllowed(type) {
  const allowedTypes = ['txt', 'pdf', 'xls', 'xlsx', 'doc', 'docx', 'ppt', 'pptx'];

  return allowedTypes.includes(type);
}
function getFileUrls(fieldValue) {

  fieldValue = flattenArray(fieldValue)

  let fileUrlsArr = []
  for (let i = 0; i < fieldValue.length; i++) {
    if (fieldValue[i].type.includes("image") || fieldValue[i].imgSize || isTypeAllowed(fieldValue[i].type)) {
      let val = (shtType == "k" ? sht : Application).Record.GetAttachmentURL({
        UploadId: fieldValue[i].uploadId,
        Source: fieldValue[i].source
      });
      if (val) {
        // 判断原始链接中是否已经有参数
        let separator = val.includes('?') ? '&' : '?';

        // 添加 type 参数
        let newUrl = val + separator + 'type=' + fieldValue[i].type;
        newUrl = `${newUrl}&filename=${fieldValue[i].fileName}`
        fileUrlsArr.push(newUrl)

      }

    }
  }
  return fileUrlsArr

}
function flattenArray(arr) {

  if (arr == "") return []
  if (!Array.isArray(arr)) {
    return arr;
  }


  const result = [];

  Array.from(arr).forEach(item => {
    if (Array.isArray(item)) {
      result.push(...flattenArray(item));
    } else {
      result.push(item);
    }
  });

  return result;
}


function updateRecords(sht, recs) {
  let sid = shtType == "k" ? sht.Id : sht.id
  let updated = (shtType == "k" ? sht : Application).Record.UpdateRecords({
    SheetId: sid,
    Records: recs
  })
  return updated || []
}



function createFiled(sht, fieldName) {

  let field;
  if (table_type == "在线工作表") {
    let t_index = parseInt(title_row_index)
    if (t_index != undefined) {

      // 获取表头的最后一列
      let colEnd = sht.Cells(t_index, sht.Columns.Count).End(-4159).Column;

      // 获取现有表头内容到 targetHeaders 数组
      let targetHeaders = Array.isArray(sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd)).Value) ? sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd)).Value[0] : [sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd)).Value];

      // 检查标题是否在 targetHeaders 中
      if (!targetHeaders.includes(fieldName)) {
        // 如果不存在，将标题写入表头的下一个空列
        colEnd++;  // 移动到下一列
        sht.Cells(t_index, colEnd).Value = fieldName;
        field = fieldName
      }

    }
  } else {

    let tempfield = {};
    tempfield["name"] = fieldName;
    tempfield["defaultValueType"] = "Normal";
    tempfield["numberFormat"] = "@";
    tempfield["type"] = "MultiLineText";

    field = (shtType == "k" ? sht : Application).Field.CreateFields({
      SheetId: sht.id ? sht.id : sht.Id,
      Fields: [
        tempfield
      ]
    })


  }
  return field
}
// 根据视图名称和类别获取视图对象
function getVieWIdWithName(sht, viewName) {
  let viewId;
  const views = Application.View.GetViews({ SheetId: sht.id });
  for (let i = 0; i < views.length; i++) {
    if (views[i].name == viewName) {
      viewId = views[i].id;
      break;
    }
  }
  return viewId;

}
function getFieldWithName(sht, fldName) {
  let field;
  if (table_type == "在线工作表") {
    let t_index = parseInt(title_row_index)
    if (t_index != undefined) {

      // 获取表头的最后一列
      let colEnd = sht.Cells(t_index, sht.Columns.Count).End(-4159).Column;

      // 获取现有表头内容到 targetHeaders 数组
      let targetHeaders = Array.isArray(sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd)).Value) ? sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd)).Value[0] : [sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd)).Value];
      console.log(targetHeaders)
      // 检查标题是否在 targetHeaders 中
      if (targetHeaders.includes(fldName)) {
        field = fldName
      }
    }
  } else {
    const fields = (shtType == "k" ? sht : Application).Field.GetFields({ SheetId: sht.id ? sht.id : sht.Id });
    for (let i = 0; i < fields.length; i++) {
      if (fields[i].name == fldName) {
        field = fields[i];
        break;
      }
    }
  }
  return field; // 返回具有指定名称的表格对象或 undefined
}
function getAllRecordsWithFilter(sht, viewid, fields, op, criterias) {
  let filter
  if (op == "Empty" || op == "NotEmpty") {
    filter = {
      "mode": "AND",
      "criteria": [{
        "field": monitor_field_name,
        "op": op,
        "values": []
      }]
    }
  } else if (op == "BeContains" || op == "NotBeContains" || op == "regex") {
    filter = null
  } else {
    filter = {
      "mode": "AND",
      "criteria": [{
        "field": monitor_field_name,
        "op": op,
        "values": [monitor_content]
      }]
    }
  }
  if (filter) {
    filter.criteria.push(...criterias)
  } else {

    filter = {
      "mode": "AND",
      "criteria": criterias
    }
  }
  console.log(filter)
  let all = [];
  let offset = null;
  let sid = shtType == "k" ? sht.Id : sht.id
  while (all.length === 0 || offset) {

    let records = (shtType == "k" ? sht : Application).Record.GetRecords({
      SheetId: sid,
      ViewId: viewid,
      Offset: offset,
      TextValue: "compound",
      Fields: fields,
      Filter: filter
    });

    offset = records.offset;
    all = all.concat(records.records);
  }

  return all;
}

/**
 * 获取具有指定名称的数据表对象。
 * @param {string} shtName - 要查找的表格名称。
 * @returns {object | undefined} 包含指定名称的表格对象，如果未找到则返回 undefined。
 */
function getShtWithName(shtName) {
  let sheet;

  const sheets = Application.Sheet.GetSheets();
  for (let i = 0; i < sheets.length; i++) {
    if (sheets[i].name == shtName) {
      sheet = sheets[i];
      break;
    }
  }

  return sheet;
}

function getFormattedDate() {
  const today = new Date();
  const options = { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' };
  const formattedDate = today.toLocaleString('zh-CN', options);
  return formattedDate;
}
function processMessages(oldMessages, newMessage) {

  if (oldMessages == '' || oldMessages == undefined || oldMessages == null) {
    return newMessage;
  }

  let messages = oldMessages.split(';;');

  let wxidNewMessage = newMessage.split('##')[1];

  let found = false;
  for (let i = 0; i < messages.length; i++) {
    // 提取当前消息中的 wxid
    let wxid = messages[i].split('##')[1];
    if (wxid === wxidNewMessage) {
      messages[i] = newMessage;
      found = true;
      break;
    }
  }

  if (!found) {
    messages.push(newMessage);
  }
  return messages.join(';;');
}


//在线工作表相关
function checkContent(content, rule, value) {
  console.log(content)
  console.log(value)
  switch (rule) {
    case '等于':
      return content === value;
    case '不等于':
      return content !== value;
    case '开头是':
      return content.startsWith(value);
    case '结尾是':
      return content.endsWith(value);
    case '包含':
      return content.includes(value);
    case '不包含':
      return !content.includes(value);
    case '为空':
      return content === '';
    case '不为空':
      return content !== '';
    default:
      return false;
  }
}
function isMatch(regexPattern, str, flags = '') {
  const regex = new RegExp(regexPattern, flags);
  return regex.test(str);
}
function normalizeRangeFilterFields(config) {
  let parsed = config;
  if (typeof config == "string" && config.trim() != "") {
    try {
      parsed = JSON.parse(config)
    } catch (e) {
      parsed = {}
    }
  }
  if (!parsed || typeof parsed != "object") {
    parsed = {}
  }
  return {
    user_field_name: parsed.user_field_name || "微信id",
    group_field_name: parsed.group_field_name || "微信群id"
  }
}
function getRangeMode(mode) {
  let m = mode
  if (typeof m == "string") {
    m = m.trim().toLowerCase()
  }
  if (!m || m == "所有" || m == "all") return "all"
  if (m == "查询人所在微信群" || m == "group") return "group"
  if (m == "查询人微信" || m == "user") return "user"
  if (m == "查询人所在微信群+查询人微信" || m == "both") return "both"
  return "all"
}
function getNotificationMode(mode) {
  let m = mode
  if (typeof m == "string") {
    m = m.trim().toLowerCase()
  }
  if (!m || m == "文本" || m == "text") return "text"
  if (m == "图片" || m == "image") return "image"
  if (m == "文件" || m == "file") return "file"
  if (m == "仪表盘-超链接" || m == "dashboard_link") return "dashboard_link"
  return "text"
}
function pushUnique(arr, value) {
  if (!arr.includes(value)) {
    arr.push(value)
  }
}
function normalizeReturnFields(config) {
  if (!config) return []
  if (Array.isArray(config)) return config.map(item => String(item)).filter(item => item)
  if (typeof config == "string") {
    let text = config.trim()
    if (!text) return []
    try {
      const parsed = JSON.parse(text)
      if (Array.isArray(parsed)) return parsed.map(item => String(item)).filter(item => item)
    } catch (e) {
    }
    return text.split(",").map(item => item.trim()).filter(item => item)
  }
  return []
}
function normalizeQueryConditions(config) {
  if (!config) return []
  if (Array.isArray(config)) return config
  if (typeof config == "string") {
    const text = config.trim()
    if (!text) return []
    try {
      const parsed = JSON.parse(text)
      return Array.isArray(parsed) ? parsed : []
    } catch (e) {
      return []
    }
  }
  return []
}
function getAllFieldNames(sht) {
  if (table_type == "在线工作表") {
    let colEnd = sht.Cells(title_row_index, sht.Columns.Count).End(-4159).Column;
    let headers = Array.isArray(sht.Range(sht.Cells(title_row_index, 1), sht.Cells(title_row_index, colEnd)).Value) ? sht.Range(sht.Cells(title_row_index, 1), sht.Cells(title_row_index, colEnd)).Value[0] : [sht.Range(sht.Cells(title_row_index, 1), sht.Cells(title_row_index, colEnd)).Value];
    return headers.filter(item => item != undefined && item !== "")
  }
  const fields = (shtType == "k" ? sht : Application).Field.GetFields({ SheetId: sht.id ? sht.id : sht.Id });
  return fields.map(item => item.name).filter(item => item != undefined && item !== "")
}
function getRecordFieldText(record, fieldName, isDimTable) {
  const f = record.fields[fieldName]
  if (isDimTable) {
    if (!f) return ""
    if (typeof f == "object") {
      if (f.text !== undefined) return f.text
      if (f.value !== undefined) return f.value
    }
    return f
  }
  return f == undefined ? "" : f
}
function toNumberValue(value) {
  if (value == undefined || value === null || value === "") return NaN
  if (typeof value == "number") return value
  const cleaned = String(value).replace(/,/g, "").trim()
  return Number(cleaned)
}
function applySingleCondition(value, condition) {
  const op = String(condition.op || condition.rule || "").toLowerCase()
  const target = condition.value
  if (op == "contains" || op == "包含") return String(value).includes(String(target))
  if (op == "not_contains" || op == "不包含") return !String(value).includes(String(target))
  if (op == "equals" || op == "eq" || op == "等于") return String(value) == String(target)
  if (op == "not_equals" || op == "neq" || op == "不等于") return String(value) != String(target)
  if (op == "gt" || op == "大于") return toNumberValue(value) > toNumberValue(target)
  if (op == "gte" || op == "大于等于") return toNumberValue(value) >= toNumberValue(target)
  if (op == "lt" || op == "小于") return toNumberValue(value) < toNumberValue(target)
  if (op == "lte" || op == "小于等于") return toNumberValue(value) <= toNumberValue(target)
  if (op == "between" || op == "范围") {
    const min = condition.min
    const max = condition.max
    const n = toNumberValue(value)
    return n >= toNumberValue(min) && n <= toNumberValue(max)
  }
  return true
}
function applyQueryConditions(records, conditions, isDimTable) {
  if (!conditions || conditions.length == 0) return records
  return records.filter(record => {
    for (let i = 0; i < conditions.length; i++) {
      const cond = conditions[i] || {}
      const field = cond.field
      if (!field) continue
      const value = getRecordFieldText(record, field, isDimTable)
      if (!applySingleCondition(value, cond)) return false
    }
    return true
  })
}
function buildRecordOutput(record, isDimTable, mode, selectedFields) {
  const row = {}
  let fields = selectedFields || []
  if (mode == "all_fields" || fields.length == 0) {
    fields = Object.keys(record.fields || {})
  }
  for (let i = 0; i < fields.length; i++) {
    const fieldName = fields[i]
    row[fieldName] = getRecordFieldText(record, fieldName, isDimTable)
  }
  return row
}
function getAllRecordsFromTableSheet1(sht, filterFields, monitor_field_rule) {
  let records = [];
  // 获取表头的最后一列
  let colEnd = sht.Cells(title_row_index, sht.Columns.Count).End(-4159).Column;

  // 获取表头内容
  let headers = Array.isArray(sht.Range(sht.Cells(title_row_index, 1), sht.Cells(title_row_index, colEnd)).Value) ? sht.Range(sht.Cells(title_row_index, 1), sht.Cells(title_row_index, colEnd)).Value[0] : [sht.Range(sht.Cells(title_row_index, 1), sht.Cells(title_row_index, colEnd)).Value];

  // 找出 filterFields 对应的列索引
  let fieldIndexes = {};
  for (let i = 0; i < headers.length; i++) {
    let header = headers[i];
    if (filterFields.includes(header)) {
      fieldIndexes[header] = i;
    }
  }

  let lastRow = sht.UsedRange.RowEnd
  if (lastRow <= title_row_index) {
    lastRow = title_row_index + 1
  }
  let data = sht.Range(sht.Cells(title_row_index + 1, 1), sht.Cells(lastRow, colEnd)).Value;
  console.log(data)
  if (!Array.isArray(data) && data) {
    data = [[data]]
  }
  console.log(data)
  for (let i = 0; i < data.length; i++) {
    let record = { fields: {} };
    let tag = false
    let tag1 = true
    if (rangeMode != "all") {
      let wechat_value
      let chatroom_value
      let colIndex
      for (let field of filterFields) {
        if (field == range_filter_fields.user_field_name) {

          colIndex = fieldIndexes[field];
          if (colIndex != undefined) {
            wechat_value = data[i][colIndex];
          }
        } else if (field == range_filter_fields.group_field_name) {
          colIndex = fieldIndexes[field];
          if (colIndex != undefined) {
            chatroom_value = data[i][colIndex];
          }
        }

      }

      switch (rangeMode) {
        case "group":
          tag1 = checkContent(chatroom_value, "包含", chatroom_id)
          break
        case "user":
          tag1 = checkContent(wechat_value, "包含", wechat_id)
          break
        case "both":
          tag1 = checkContent(chatroom_value, "包含", chatroom_id) && checkContent(wechat_value, "包含", wechat_id)
          break
      }
    }

    for (let field of filterFields) {
      let colIndex = fieldIndexes[field];
      if (colIndex != undefined) {
        let value = data[i][colIndex];
        record.fields[field] = value;
        record.id = i + title_row_index + 1 //行号

        if (field == notification_field_name) {
          record.n_cid = colIndex + 1
        }


        if (monitor_field_rule == "被包含" || monitor_field_rule == "不被包含" || monitor_field_rule == "正则表达式") {
          tag = true
        } else {
          if (field == monitor_field_name) {
            console.log(field)

            if (checkContent(value, monitor_field_rule, monitor_content)) {
              tag = true
            }
          }
        }

      }
    }
    if (tag && tag1) {
      records.push(record);
    }

  }

  return records;
}
