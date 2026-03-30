const targetSheetName = Context.argv.sheet_name || Context.argv.table_name || "";
const includeRaw = Context.argv.include_raw === true || Context.argv.include_raw === "true" || Context.argv.include_raw === "是";

function getSheetByName(name) {
  const sheets = Application.Sheet.GetSheets();
  for (let i = 0; i < sheets.length; i++) {
    if (sheets[i].name === name) {
      return sheets[i];
    }
  }
  return null;
}

function normalizeField(field) {
  function pick(obj, keys) {
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      if (obj[k] !== undefined) return obj[k];
    }
    return undefined;
  }
  const result = {
    id: pick(field, ["id", "Id", "fieldId", "FieldId"]),
    name: pick(field, ["name", "Name", "fieldName", "FieldName"]),
    type: pick(field, ["type", "Type", "fieldType", "FieldType"]),
    defaultValueType: pick(field, ["defaultValueType", "DefaultValueType"]),
    numberFormat: pick(field, ["numberFormat", "NumberFormat"])
  };

  const optionalKeys = [
    "displayStyle",
    "displayText",
    "items",
    "max",
    "linkSheet",
    "multipleLinks",
    "multipleContacts",
    "noticeNewContact",
    "formula",
    "precision",
    "currencySymbol",
    "dateFormat",
    "timeFormat",
    "isPrimary",
    "required"
  ];

  for (let i = 0; i < optionalKeys.length; i++) {
    const key = optionalKeys[i];
    const upperKey = key.charAt(0).toUpperCase() + key.slice(1);
    const val = pick(field, [key, upperKey]);
    if (val !== undefined) {
      result[key] = val;
    }
  }

  return result;
}

if (!targetSheetName) {
  return {
    respData: {
      state: "error",
      message: "缺少参数 sheet_name 或 table_name"
    }
  };
}

const targetSheet = getSheetByName(targetSheetName);
if (!targetSheet) {
  const allSheets = Application.Sheet.GetSheets().map(item => ({ id: item.id, name: item.name }));
  return {
    respData: {
      state: "error",
      message: "未找到指定多维表",
      target_sheet_name: targetSheetName,
      available_sheets: allSheets
    }
  };
}

const fields = Application.Field.GetFields({ SheetId: targetSheet.id }) || [];
const normalizedFields = fields.map(normalizeField);

const response = {
  state: "success",
  sheet: {
    id: targetSheet.id,
    name: targetSheet.name
  },
  count: normalizedFields.length,
  fields: normalizedFields
};

if (includeRaw) {
  response.raw_fields = fields;
}

return { respData: response };
