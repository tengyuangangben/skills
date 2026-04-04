/*
 * 通用录入脚本（WPS 多维表 / 在线工作表）
 * 适用场景：通过外部 API 调用本脚本，将结构化数据写入指定数据表
 * 版本日期：2026-03-30
 *
 * 入参约定（Context.argv）：
 * - sheet_name: 目标数据表名称
 * - table_type: "多维表" 或 "在线工作表"
 * - request_type: "content"（录入）/ "delete_record"（按请求ID删除）
 * - request_id: 外部请求唯一标识，用于幂等与回滚删除
 * - fields: 二维数组，每个元素代表一条记录的字段数组
 * - full_input_mode: 全量录入模式开关（true/false）
 * - submitter/submit_channel: 提交元数据
 *
 * 出参约定：
 * - respData: 处理结果（字符串或结构化对象）
 * - rid: 首条写入记录ID（在线工作表返回行号）
 * - sid: 数据表ID（在线工作表为空）
 * - rec_link: 分享链接（开启 enable_feedback_link 时返回）
 */

const submitterFieldName = '_提交人';
const submitChannelFieldName = '_提交渠道';
const requestIdFieldName = "_请求ID";
const originalAttackmentFieldName = "_原始附件";
const autoCreatableSystemFields = [requestIdFieldName, submitterFieldName, submitChannelFieldName];
function canAutoCreateField(fieldName) {
  return autoCreatableSystemFields.indexOf(fieldName) >= 0
}
const row_fields_data = Context.argv.fields;

const table_type = Context.argv.table_type;
const full_input_return_status = Context.argv.full_input_return_status;
const full_input_return_message = Context.argv.full_input_return_message;
const title_row_index = Context.argv.title_row_index
const shtType = Application.FileInfo.officeType
let shtName = Context.argv.sheet_name;

if (Array.isArray(row_fields_data)) { //检测有没有数据表名键
  if (row_fields_data.length > 0) {
    const matched = row_fields_data[0].find(item => item.field_name === '数据表名' && item.value !== '');
    shtName = matched ? matched.value : shtName;
  }
}


const original_content = Context.argv.original_content || Context.argv.original_msg || ""
const request_type = Context.argv.request_type;
const enable_feedback_link = Context.argv.enable_feedback_link
const overwrite_mode = Context.argv.overwrite_mode
const upload_file = Context.argv.upload_file
const submitter = Context.argv.submitter || Context.argv.nickname || ""
const submit_channel = Context.argv.submit_channel || Context.argv.chatroom_id || ""
const request_id = Context.argv.request_id || Context.argv.msg_id || ""
const file_base64 = Context.argv.file_base64
const full_input_mode = Context.argv.full_input_mode // 全部录入模式标志
const allow_new_fields = Context.argv.allow_new_fields
const new_fields_whitelist = Array.isArray(Context.argv.new_fields_whitelist) ? Context.argv.new_fields_whitelist : []
function isTrueValue(v) {
  if (v === true) return true
  if (v === false || v == null) return false
  const s = String(v).trim().toLowerCase()
  return s == "1" || s == "true" || s == "yes" || s == "y" || s == "是"
}
function canCreateBusinessField(fieldName) {
  if (!isTrueValue(allow_new_fields)) return false
  if (!Array.isArray(new_fields_whitelist) || new_fields_whitelist.length == 0) return true
  return new_fields_whitelist.includes(fieldName)
}
if (request_type == "delete_record") {
  let sht = shtType != "d" ? Application.Sheets(shtName) : getShtWithName(shtName);
  if (shtType != "d") {
    sht.Activate()
  }
  let delete_request_id = Context.argv.request_id || Context.argv.msg_id
  if (delete_request_id) {
    let recs = getAllRecordsWithFilter3(sht, requestIdFieldName, delete_request_id)
    if (recs[0]) {
      let ids = recs.map(item => item.id)
      let deleted_recs = deleteRecords(sht, ids)
      if (deleted_recs) {
        return { "respData": { "state": "success" }, "msg": "删除成功", "deleted_length": deleted_recs.length }
      } else {
        return { "respData": { "state": "error" }, "msg": "删除失败请重试", "deleted_length": 0 }
      }
    } else {
      return { "respData": { "state": "error" }, "msg": "未找到对应记录", "deleted_length": 0 }
    }
  }

}
else {

  const monitor_field_name = Context.argv.check_field_name; //验证字段
  const monitor_field_rule = Context.argv.check_field_rule;//验证规则
  const monitor_content = Context.argv.success_threshold;//验证内容
  const notification_field_name = Context.argv.return_field_name; //返回字段
  // try {
  let sht = shtType != "d" ? Application.Sheets(shtName) : getShtWithName(shtName);
  if (shtType != "d") {
    sht.Activate()
  }
  
  // 全部录入模式：外部传什么就按一条完整记录写入什么，常用于简单接口直写
  if (full_input_mode === true || full_input_mode === "true" || full_input_mode === "是") {
    let response = main_full_input()
    // 如果开启返回录入状态，则附加统一的反馈消息（供后端转发到微信）
    if (full_input_return_status === true || full_input_return_status === "true" || full_input_return_status === "是") {
      const baseMsg = (full_input_return_message && String(full_input_return_message).trim()) || "✅ 录入成功\n已录入";
      if (response && typeof response === "object") {
        if (!response.message) {
          response.message = baseMsg;
        }
        if (!response.respData) {
          response.respData = baseMsg;
        }
      }
    }
    return response
  } else {
    let response = main()
    return response
  }


  // 全部录入模式主函数
  function main_full_input() {
    const messageFieldName = "消息"
    const attachmentFieldName = "附件"
    
    // 确保"消息"和"附件"字段存在
    sht = shtType != "d" ? Application.Sheets(shtName) : getShtWithName(shtName);
    if (shtType != "d") {
      sht.Activate()
    }
    
    // 创建"消息"字段（文本类型）
    let fld = getFieldWithName(sht, messageFieldName);
    if (!fld) {
      createFiled(sht, messageFieldName);
      Time.sleep(500); // 等待字段创建完成
    }
    
    // 创建"附件"字段（附件类型，仅多维表支持，如果有附件就创建）
    if (file_base64 && table_type == "多维表" && shtType == "d") {
      fld = getFieldWithName(sht, attachmentFieldName);
      if (!fld) {
        createAttachmentFiled(sht, attachmentFieldName);
        Time.sleep(500); // 等待字段创建完成
      }
    }
    
    // 创建系统字段
    fld = getFieldWithName(sht, submitterFieldName);
    if (!fld) {
      createFiled(sht, submitterFieldName);
      Time.sleep(300);
    }
    fld = getFieldWithName(sht, submitChannelFieldName);
    if (!fld) {
      createFiled(sht, submitChannelFieldName);
      Time.sleep(300);
    }
    fld = getFieldWithName(sht, requestIdFieldName);
    if (!fld) {
      createFiled(sht, requestIdFieldName);
      Time.sleep(300);
    }
    // 在线工作表：创建 _创建时间 字段
    if (table_type == "在线工作表") {
      fld = getFieldWithName(sht, "_创建时间");
      if (!fld) {
        createFiled(sht, "_创建时间");
        Time.sleep(300);
      }
    }
    
    // 所有字段创建完成后，重新获取 sheet 对象，确保字段已创建
    sht = shtType != "d" ? Application.Sheets(shtName) : getShtWithName(shtName);
    if (shtType != "d") {
      sht.Activate()
    }
    
    // 构建记录数据
    const fields = {};
    // 确保所有字段值都是字符串类型，避免 null 或 undefined
    fields[messageFieldName] = (original_content != null && original_content !== undefined) ? String(original_content) : "";
    fields[submitterFieldName] = (submitter != null && submitter !== undefined) ? String(submitter) : "";
    fields[submitChannelFieldName] = (submit_channel != null && submit_channel !== undefined) ? String(submit_channel) : "";
    fields[requestIdFieldName] = (request_id != null && request_id !== undefined) ? String(request_id) : "";
    // 在线工作表：写入 _创建时间 字段
    if (table_type == "在线工作表") {
      fields["_创建时间"] = new Date().toISOString();
    }
    
    // 处理附件：如果有 file_base64，写入附件字段（仅多维表支持）
    if (file_base64 && table_type == "多维表" && shtType == "d") {
      // 附件字段先设为空，稍后单独写入
      fields[attachmentFieldName] = "";
    }
    
    // 添加记录
    if (table_type != "在线工作表") {
      let s = Application.Sheets(shtName)
      let link = ""
      if (table_type == "多维表") {
        try {
          if (enable_feedback_link == "是") {
            let views = s.Views
            if (!isViewExist(s, "_录入接口分享专用")) {
              const addedView = views.Add('Grid', '_录入接口分享专用')
              const viewShare = addedView.ViewShare
              let req = viewShare.SetEnable(true)
              viewShare.ChangePermission('anyone', 'read')
              link = viewShare.ShareUrl
            } else {
              let view = getViewWithName(s, "_录入接口分享专用")
              const viewShare = view.ViewShare
              let req = viewShare.SetEnable(true)
              viewShare.ChangePermission('anyone', 'read')
              link = view.ViewShare.ShareUrl
            }
          }
        } catch (e) { }
      }
      
      let recs = [{ "fields": fields }]
      let added = addRecords(sht, recs)
      Time.sleep(1000)
      
      if (added[0]) {
        // 如果有附件，写入附件字段（仅多维表支持）
        if (file_base64 && table_type == "多维表" && shtType == "d") {
          try {
            Time.sleep(1000) // 等待记录创建完成
            const record_id = added[0].id
            // 构建附件数据：file_base64 应该是 data:mime;base64,xxx 格式
            const fileList = [{
              fileData: file_base64,
              fileName: original_content || "附件"
            }]
            Application.Sheets(shtName).RecordRange(record_id, `@${attachmentFieldName}`).Value = DBCellValue(fileList)
            Time.sleep(500) // 等待附件写入完成
          } catch (e) {
            // 写入失败，静默处理
          }
        }
        
        return { "respData": "录入成功", "rid": added[0].id, "sid": s.Id, "rec_link": link }
      }
    } else {
      // 在线工作表：直接写入
      let addedRowIndexArr = writeDataToNewRow(sht, title_row_index, [fields]);
      return { "respData": "录入成功", "rid": addedRowIndexArr[0], "sid": "", "rec_link": "" }
    }
    
    return { "respData": "录入失败", "rid": "", "sid": "", "rec_link": "" }
  }

  // 普通录入模式主函数
  // 支持一次写入多条记录，支持字段自动创建、录入后校验、附件二次写入
  function main() {

    // 如果检测字段名称为空，跳过字段创建和检测逻辑
    if (monitor_field_name && monitor_field_name.trim() !== "") {
      let fld = getFieldWithName(sht, monitor_field_name);
      if (!fld) {
        return { "respData": `录入失败：字段不存在 ${monitor_field_name}`, "rid": "", "sid": "", "rec_link": "" }
      }
    }

    fld = getFieldWithName(sht, requestIdFieldName);

    if (!fld) {

      createFiled(sht, requestIdFieldName);
    }

    sht = shtType != "d" ? Application.Sheets(shtName) : getShtWithName(shtName);
    // 只有传了 notification_field_name 才检查和创建
    if (notification_field_name && notification_field_name.trim() !== "") {
      fld = getFieldWithName(sht, notification_field_name);
      if (!fld) {
        return { "respData": `录入失败：字段不存在 ${notification_field_name}`, "rid": "", "sid": "", "rec_link": "" }
      }
    }
    sht = shtType != "d" ? Application.Sheets(shtName) : getShtWithName(shtName);
    fld = getFieldWithName(sht, submitterFieldName);
    if (!fld) {
      createFiled(sht, submitterFieldName);
    }

    fld = getFieldWithName(sht, submitChannelFieldName);
    if (!fld) {
      createFiled(sht, submitChannelFieldName);
    }
    // 在线工作表：创建 _创建时间 字段
    if (table_type == "在线工作表") {
      fld = getFieldWithName(sht, "_创建时间");
      if (!fld) {
        return { "respData": `录入失败：字段不存在 _创建时间`, "rid": "", "sid": "", "rec_link": "" }
      }
    }
    const fields_arr = []
    const image_fields_info = [] // 存储图片字段信息，用于后续处理
    const invalid_fields = {}
    
    Array.from(row_fields_data).forEach((fields_data, record_index) => {
      const fields = {};
      fields_data.forEach(item => {
        fld = getFieldWithName(sht, item.field_name);
        if (!fld) {
          if (canAutoCreateField(item.field_name)) {
            createFiled(sht, item.field_name);
            fld = getFieldWithName(sht, item.field_name);
          } else if (canCreateBusinessField(item.field_name)) {
            if (table_type == "在线工作表") {
              createFiled(sht, item.field_name);
            } else {
              if (item.field_format == "数字") {
                createNumberFiled(sht, item.field_name)
              } else if (item.field_format == "图片" || item.field_format == "附件") {
                createAttachmentFiled(sht, item.field_name)
              } else {
                createFiled(sht, item.field_name);
              }
            }
            fld = getFieldWithName(sht, item.field_name);
          } else {
            invalid_fields[item.field_name] = true
            return
          }
        }
        if (!fld) return
        
        // 处理图片/附件字段：从图片/附件字段的 file_base64 和 file_name 读取
        // 兼容旧配置：字段格式为"图片"也视为附件字段
        if ((item.field_format == "图片" || item.field_format == "附件") && table_type == "多维表" && request_type == "content") {
          // 图片字段在多维表中需要特殊处理，先不在这里赋值
          // 稍后在添加记录后单独处理
          fields[item.field_name] = ""; // 先设为 null，稍后处理
          
          // 从图片字段的 file_base64 和 file_name 读取数据
          const field_file_base64 = item.file_base64 || ''
          const field_file_name = item.file_name || ''
          
          if (field_file_base64 && field_file_name) {
            // 解析用 ||| 分隔的 file_base64 和 file_name
            const fileDataArray = field_file_base64.split('|||')
            const fileNameArray = field_file_name.split('|||')
            
            // 构建文件对象数组
            const fileList = []
            for (let i = 0; i < fileDataArray.length; i++) {
              if (fileDataArray[i] && fileNameArray[i]) {
                // 检查 fileData 是否包含 MIME 类型前缀
                const fileData = fileDataArray[i]
                const fileName = fileNameArray[i]
                fileList.push({
                  fileData: fileData,  // 应该是 data:image/jpeg;base64,xxx 格式
                  fileName: fileName
                })
              }
            }
            
            if (fileList.length > 0) {
              image_fields_info.push({
                record_index: record_index,
                field_name: item.field_name,
                fileList: fileList
              })
            }
          }
        } else {
          fields[item.field_name] = item.value;
        }
      })


      fields[submitterFieldName] = submitter;
      fields[submitChannelFieldName] = submit_channel
      fields[requestIdFieldName] = request_id
      // 在线工作表：写入 _创建时间 字段
      if (table_type == "在线工作表") {
        fields["_创建时间"] = new Date().toISOString();
      }
      fields_arr.push(fields)
    })
    const invalid_names = Object.keys(invalid_fields)
    if (invalid_names.length > 0) {
      return { "respData": `录入失败：以下字段不存在且不允许自动创建 ${invalid_names.join(",")}`, "rid": "", "sid": "", "rec_link": "" }
    }

    if (table_type != "在线工作表") {
      let s = Application.Sheets(shtName)
      let link = ""
      if (table_type == "多维表") {
        try {
          if (enable_feedback_link == "是") {
            let views = s.Views
            if (!isViewExist(s, "_录入接口分享专用")) {
              const addedView = views.Add('Grid', '_录入接口分享专用')
              const viewShare = addedView.ViewShare
              let req = viewShare.SetEnable(true)
              viewShare.ChangePermission('anyone', 'read')
              link = viewShare.ShareUrl
            } else {
              let view = getViewWithName(s, "_录入接口分享专用")
              const viewShare = view.ViewShare
              let req = viewShare.SetEnable(true)
              viewShare.ChangePermission('anyone', 'read')
              link = view.ViewShare.ShareUrl
            }

          }
        } catch (e) { }
      }
      let recs = []
      fields_arr.forEach(item => {
        recs.push({ "fields": item })
      })
      let added = addRecords(sht, recs) //这是旧方法添加记录
      Time.sleep(1000)
      if (added[0]) {
        let respdata = ""
        let respdata_arr = []  // 用于存储多条记录的返回值
        let delay_seconds = parseInt(Context.argv.delay_seconds)
        if (delay_seconds > 0) {
          Time.sleep(delay_seconds * 1000)
        }

        let delete_tag = false
        // 如果检测字段名称为空，跳过检测逻辑，直接录入
        if (monitor_field_name && monitor_field_name.trim() !== "") {
          for (let idx = 0; idx < added.length; idx++) {
            const added_data = added[idx];
            let single_resp = "";

            let content = added_data.fields[monitor_field_name] ? added_data.fields[monitor_field_name].text : "";
            if (delay_seconds > 0 && shtType == "d") { //延迟仅支持多维表
              try {
                single_resp = s.RecordRange(added_data.id, `@${notification_field_name}`).Text
              } catch (e) {

              }


            } else {
              single_resp = added_data.fields[notification_field_name] ? added_data.fields[notification_field_name].text : "";
            }
            
            // 收集每条记录的返回值（带序号）
            if (notification_field_name && notification_field_name.trim() !== "" && single_resp) {
              respdata_arr.push(`${idx + 1}.${single_resp}`);
            }

            if (!checkContent(content, monitor_field_rule, monitor_content)) {
              delete_tag = true
              break
            }
          }
        } else {
          // 检测字段为空，直接获取返回字段内容
          for (let idx = 0; idx < added.length; idx++) {
            const added_data = added[idx];
            let single_resp = "";
            if (delay_seconds > 0 && shtType == "d") { //延迟仅支持多维表
              try {
                single_resp = s.RecordRange(added_data.id, `@${notification_field_name}`).Text
              } catch (e) {

              }
            } else {
              single_resp = added_data.fields[notification_field_name] ? added_data.fields[notification_field_name].text : "";
            }
            
            // 收集每条记录的返回值（带序号）
            if (notification_field_name && notification_field_name.trim() !== "" && single_resp) {
              respdata_arr.push(`${idx + 1}.${single_resp}`);
            }
          }
        }
        
        // 多条记录时按序号拼接，单条记录时不加序号
        if (respdata_arr.length > 1) {
          respdata = respdata_arr.join("\n");
        } else if (respdata_arr.length === 1) {
          respdata = respdata_arr[0].substring(2);  // 去掉 "1." 前缀
        }

        if (delete_tag) {//检测失败时执行回滚删除
          let del = deleteRecords(sht, Array.from(added).map(item => item.id))
          if (del[0]) {
            return {
              "respData": { "state": "error", "msg": "记录不符合要求，已删除，请重新录入", "deleted": true },
              "rid": "",
              "sid": s.Id,
              "rec_link": ""
            }
          } else {
            return {
              "respData": { "state": "error", "msg": "记录不符合要求，但删除失败，请联系管理员", "deleted": false },
              "rid": "",
              "sid": s.Id,
              "rec_link": ""
            }
          }
        } else { //添加附件
          // 处理图片字段：在记录添加后，单独写入图片（一次性录入模式）
          if (image_fields_info.length > 0 && request_type == "content") {
            image_fields_info.forEach(img_info => {
              try {
                const record_index = img_info.record_index
                
                if (added[record_index] && added[record_index].id) {
                  const record_id = added[record_index].id
                  const field_name = img_info.field_name
                  const fileList = img_info.fileList
                  
                  // 写入多张图片到图片字段
                  Application.Sheets(shtName).RecordRange(record_id, `@${field_name}`).Value = DBCellValue(fileList)
                }
              } catch (e) {
                // 写入失败，静默处理
              }
            })
            Time.sleep(500) // 等待图片写入完成
          }
          
          // 处理原始附件字段：批量录入时，为每条记录都写入原始附件
          if (upload_file == "是" && file_base64 && shtType == "d") {
            Time.sleep(1000)
            // 循环为每条记录写入原始附件
            added.forEach((added_rec, idx) => {
              try {
                if (added_rec && added_rec.id) {
                  const added_rec_id = added_rec.id
                  Application.Sheets(shtName).RecordRange(added_rec_id, `@${originalAttackmentFieldName}`).Value = DBCellValue([{ fileData: file_base64, fileName: original_content || "附件" }])
                }
              } catch (e) {
                // 写入失败，静默处理
              }
            })
          }
        }
        return { "respData": respdata, "rid": added[0].id, "sid": s.Id, "rec_link": link }

      }
    } else { //在线工作表
      let addedRowIndexArr = writeDataToNewRow(sht, title_row_index, fields_arr);
      let mindex = monitor_field_name && monitor_field_name.trim() !== "" ? getColumnIndexByHeader(sht, monitor_field_name, title_row_index) : -1
      let nindex = getColumnIndexByHeader(sht, notification_field_name, title_row_index)
      let delete_tag = false
      // 如果检测字段名称为空，跳过检测逻辑，直接录入
      if (monitor_field_name && monitor_field_name.trim() !== "" && mindex > 0) {
        for (const added_index of addedRowIndexArr) {
          let content = sht.Cells(added_index, mindex).Text
          if (!checkContent(content, monitor_field_rule, monitor_content)) {
            delete_tag = true
            break
          }
        }
      }
      let delay_seconds = Context.argv.delay_seconds
      if (delay_seconds > 0) {
        Time.sleep(delay_seconds * 1000)
      }
      let respdata = nindex > 0 ? sht.Cells(addedRowIndexArr[0], nindex).Text : ""
      if (delete_tag) {
        let startRow = Math.min(...addedRowIndexArr);
        let endRow = Math.max(...addedRowIndexArr);

        // 删除从 startRow 到 endRow 的连续多行
        sht.Range(sht.Cells(startRow, 1), sht.Cells(endRow, 1)).EntireRow.Delete();
        return { "respData": { "state": "error", "msg": "记录不符合要求，已删除，请重新录入", "deleted": true }, "rid": "", "sid": "", "rec_link": "" }
      }
      return { "respData": respdata, "rid": addedRowIndexArr[0], "sid": "", "rec_link": "" }

    }
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
    default:
      return 'Equals';
  }
}
function checkContent(content, rule, value) {
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
function updateRecords(sht, recs) {
  let updated = (shtType == "k" ? sht : Application).Record.UpdateRecords({
    SheetId: sht.id ? sht.id : sht.Id,
    Records: recs
  })
  return updated || []
}
function deleteRecords(sht, ids) {
  let deleted = (shtType == "k" ? sht : Application).Record.DeleteRecords({
    SheetId: sht.id ? sht.id : sht.Id,
    RecordIds: ids
  })
  return deleted || []
}
function addRecords(sht, recs) {
  let update_rec_arr = [];
  if (overwrite_mode == "是") {

    let keyName = Object.keys(recs[0].fields)[0]
    let field = Sheets(shtName).FieldDescriptors(`@${keyName}`)
    let fieldIsAutoNumber = false
    if (field.Type == "AutoNumber") fieldIsAutoNumber = true
    let keys = Array.from(recs).map(item => fieldIsAutoNumber ? item.fields[keyName].toString().padStart(6, '0') : item.fields[keyName])
    let filter_recs = getAllRecordsWithFilter2(sht, keyName, keys)


    // 遍历 filter_recs，检查是否在 recs 中
    if (filter_recs[0]) {
      Array.from(filter_recs).forEach(filterRec => {
        let matchIndex = Array.from(recs).findIndex(rec => rec.fields[keyName] === filterRec.fields[keyName]);
        if (matchIndex !== -1) {
          // 添加 `id` 属性并推送到 update_rec_arr
          let matchedRec = { ...recs[matchIndex], id: filterRec.id };
          Reflect.deleteProperty(matchedRec.fields, keyName)
          update_rec_arr.push(matchedRec);
          // 从 recs 删除已经添加的记录
          recs.splice(matchIndex, 1);
        }
      });
    }
  }
  let added = (shtType == "k" ? sht : Application).Record.CreateRecords({
    SheetId: sht.id ? sht.id : sht.Id,
    TextValue: "compound",
    Records: recs
  })
  let updated = (shtType == "k" ? sht : Application).Record.UpdateRecords({
    SheetId: sht.id ? sht.id : sht.Id,
    TextValue: "compound",
    Records: update_rec_arr
  })

  return [...(added || []), ...(updated || [])]
}



function createFiled(sht, fieldName) {

  let field;
  if (table_type == "在线工作表") {
    let t_index = parseInt(title_row_index)
    if (t_index) {

      // 获取表头的最后一列
      let colEnd = sht.Cells(t_index, sht.Columns.Count).End(-4159).Column;
      if (colEnd == 1 && sht.Cells(t_index, colEnd).Text == "") {
        colEnd = 0
      }
      // 获取现有表头内容到 targetHeaders 数组
      let targetHeaders = colEnd <= 1 ? sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd == 0 ? 1 : colEnd)).Value : sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd)).Value[0];
      if (!Array.isArray(targetHeaders)) {
        targetHeaders = [targetHeaders]
      }
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
function createNumberFiled(sht, fieldName) {

  let field;
  let tempfield = {};
  tempfield["name"] = fieldName;
  tempfield["defaultValueType"] = "Normal";
  tempfield["numberFormat"] = "0.0000_ ";
  tempfield["type"] = "Number";

  field = (shtType == "k" ? sht : Application).Field.CreateFields({
    SheetId: sht.id ? sht.id : sht.Id,
    Fields: [
      tempfield
    ]
  })

  return field
}
function createAttachmentFiled(sht, fieldName) {

  let field;
  let tempfield = {};
  tempfield["name"] = fieldName;
  tempfield["defaultValueType"] = "Normal";
  tempfield["numberFormat"] = "@";
  tempfield["type"] = "Attachment";
  tempfield["displayStyle"] = "Pic"

  field = (shtType == "k" ? sht : Application).Field.CreateFields({
    SheetId: sht.id ? sht.id : sht.Id,
    Fields: [
      tempfield
    ]
  })

  return field
}
function getFieldWithName(sht, fldName) {

  let field;
  if (table_type == "在线工作表") {
    let t_index = parseInt(title_row_index)
    if (t_index) {

      // 获取表头的最后一列
      let colEnd = sht.Cells(t_index, sht.Columns.Count).End(-4159).Column;

      // 获取现有表头内容到 targetHeaders 数组
      let targetHeaders = colEnd == 1 ? sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd)).Value : sht.Range(sht.Cells(t_index, 1), sht.Cells(t_index, colEnd)).Value[0];
      if (!Array.isArray(targetHeaders)) {
        targetHeaders = [targetHeaders]
      }
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
function getAllRecordsWithFilter(sht) {
  let all = [];
  let offset = null;
  while (all.length === 0 || offset) {

    let records = (shtType == "k" ? sht : Application).Record.GetRecords({
      SheetId: sht.id ? sht.id : sht.Id,
      Offset: offset,
      TextValue: "compound",
      Fields: [feedback_field_name, notification_field_name, monitor_field_name],
      Filter: {
        "mode": "AND",
        "criteria": [
          {
            "field": monitor_field_name,
            "op": "Contains",
            "values": [monitor_content]
          },
          {
            "field": feedback_field_name,
            "op": "NotEqu",
            "values": [success_feedback]
          }

        ]
      },
    });

    offset = records.offset;
    all = all.concat(records.records);
  }

  return all;
}
/**主要是用来覆盖录入 筛选存在的值 */
function getAllRecordsWithFilter2(sht, field, values) {
  let all = [];
  let offset = null;
  while (all.length === 0 || offset) {

    let records = (shtType == "k" ? sht : Application).Record.GetRecords({
      SheetId: sht.id ? sht.id : sht.Id,
      Offset: offset,
      Fields: [field],
      Filter: {
        "mode": "AND",
        "criteria": [
          {
            "field": field,
            "op": "Intersected",
            "values": values
          }


        ]
      },
    });

    offset = records.offset;
    all = all.concat(records.records);
  }

  return all;
}

/**主要是用来筛选请求ID并删除数据 */
function getAllRecordsWithFilter3(sht, field, value) {
  let all = [];
  let offset = null;
  while (all.length === 0 || offset) {

    let records = (shtType == "k" ? sht : Application).Record.GetRecords({
      SheetId: sht.id ? sht.id : sht.Id,
      Offset: offset,
      Fields: [field],
      Filter: {
        "mode": "AND",
        "criteria": [
          {
            "field": field,
            "op": "Equals",
            "values": [value]
          }


        ]
      },
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
function writeDataToNewRow(sht, title_row_index, data_list) {
  sht.Activate();

  // 获取表头的最后一列
  let colEnd = sht.Cells(title_row_index, sht.Columns.Count).End(-4159).Column;

  // 获取表头内容
  let headers = sht.Range(sht.Cells(title_row_index, 1), sht.Cells(title_row_index, colEnd)).Value[0];

  // 初始化最大行号
  let maxRow = title_row_index;

  // 存储已插入的行号
  let insertedRows = [];

  // 遍历整个 data_list 的数据
  for (let data of data_list) {
    // 遍历单个 JSON 数据的键
    for (let key in data) {
      // 查找表头中对应的列
      let colIndex = headers.indexOf(key) + 1; // 列索引从1开始

      // 如果找到对应的列
      if (colIndex > 0) {
        // 获取该列的最后一个单元格的行号
        let lastRow = sht.Cells(sht.Rows.Count, colIndex).End(-4162).Row; // -4162 是xlUp的枚举值

        // 更新最大行号
        if (lastRow > maxRow) {
          maxRow = lastRow;
        }
      }
    }

    // 新的行号为最大行号 + 1
    let newRow = maxRow + 1;

    // 再次遍历 JSON 数据并写入到相应的列
    for (let key in data) {
      let colIndex = headers.indexOf(key) + 1;
      if (colIndex > 0) {
        sht.Cells(newRow, colIndex).NumberFormat = "@"; // 设置格式为文本
        sht.Cells(newRow, colIndex).Value = data[key];
      }
    }

    // 记录已插入的行号
    insertedRows.push(newRow);

    // 更新最大行号为刚插入的行
    maxRow = newRow;
  }

  // 返回插入的行号数组
  return insertedRows;
}
// function writeDataToNewRow(sht, title_row_index, data) {
//   sht.Activate()
//   // 获取表头的最后一列
//   let colEnd = sht.Cells(title_row_index, sht.Columns.Count).End(-4159).Column;

//   // 获取表头内容
//   let headers = sht.Range(sht.Cells(title_row_index, 1), sht.Cells(title_row_index, colEnd)).Value[0];

//   // 初始化最大行号
//   let maxRow = title_row_index;

//   // 遍历 JSON 数据的键
//   for (let key in data) {
//     // 查找表头中对应的列
//     let colIndex = headers.indexOf(key) + 1; // 列索引从1开始

//     // 如果找到对应的列
//     if (colIndex > 0) {
//       // 获取该列的最后一个单元格的行号
//       let lastRow = sht.Cells(sht.Rows.Count, colIndex).End(-4162).Row; // -4162 是xlUp的枚举值

//       // 更新最大行号
//       if (lastRow > maxRow) {
//         maxRow = lastRow;
//       }
//     }
//   }

//   // 新的行号为最大行号 + 1
//   let newRow = maxRow + 1;

//   // 再次遍历 JSON 数据并写入到相应的列
//   for (let key in data) {
//     let colIndex = headers.indexOf(key) + 1;
//     if (colIndex > 0) {
//       sht.Cells(newRow, colIndex).Value = data[key];
//     }
//   }

//   return newRow;
// }
function getColumnIndexByHeader(sht, headerName, title_row_index) {
  // 获取表头的最后一列
  let colEnd = sht.Cells(title_row_index, sht.Columns.Count).End(-4159).Column;

  // 获取表头内容
  let headers = sht.Range(sht.Cells(title_row_index, 1), sht.Cells(title_row_index, colEnd)).Value[0];

  // 查找表头名对应的列索引
  let colIndex = headers.indexOf(headerName) + 1; // 列索引从1开始

  // 如果找到对应列，返回列号；否则返回 -1 表示未找到
  return colIndex > 0 ? colIndex : -1;
}

function isViewExist(sht, viewName) {
  let tag = false
  for (let i = 1; i <= sht.Views.Count; i++) {

    if (sht.Views(i).Name == viewName) {
      tag = true
    }
  }
  return tag
}
function getViewWithName(sht, viewName) {
  let view
  for (let i = 1; i <= sht.Views.Count; i++) {

    if (sht.Views(i).Name == viewName) {
      view = sht.Views(i)
    }
  }
  return view
}
