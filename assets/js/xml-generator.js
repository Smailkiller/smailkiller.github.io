// =========================
// Helpers
// =========================
const $ = (id) => document.getElementById(id);

const SIGNATURE_COMMENT = 'XML сформирован инструментом автора. Канал: https://t.me/SMailsPub';

function safeUUID(){
  if (window.crypto && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return "id_" + Math.random().toString(16).slice(2) + "_" + Date.now();
}

function escapeXml(s){
  if (s === null || s === undefined) return "";
  return String(s)
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll("\"","&quot;")
    .replaceAll("'","&apos;");
}

function isNonEmpty(v){ return v !== null && v !== undefined && String(v).trim() !== ""; }

function toDecimalOrNull(v){
  if (!isNonEmpty(v)) return null;
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  return n;
}

function toPosIntOrNull(v){
  if (!isNonEmpty(v)) return null;
  const n = Number(v);
  if (!Number.isInteger(n) || n <= 0) return null;
  return n;
}

function fmtDecimal(v){
  if (v === null || v === undefined) return null;
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  return String(n);
}

function addSignatureCommentToXml(xmlText){
  if (!xmlText || !xmlText.trim()) return xmlText;
  if (xmlText.includes("t.me/SMailsPub")) return xmlText; // защита от дубля

  const comment = `\n\t<!-- ${SIGNATURE_COMMENT} -->\n`;

  // Вставляем перед закрывающим корневым тегом
  const closeTag = "</ArchitecturalUrbanPlanningSolution>";
  if (xmlText.includes(closeTag)){
    return xmlText.replace(closeTag, comment + closeTag);
  }

  // fallback: если вдруг корневой тег другой/не найден — просто дописываем в конец
  return xmlText.trimEnd() + `\n<!-- ${SIGNATURE_COMMENT} -->\n`;
}

function setXmlState(ok){
  $("xmlState").textContent = ok ? "✔️ XML сформирован" : "❌XML не сформирован";
  $("btnDownload").disabled = !ok;
  $("btnCopyXml").disabled = !ok;
  $("xmlState").style.borderColor = ok ? "rgba(124,107,81,0.55)" : "rgba(226,206,174,0.22)";
  $("xmlState").style.background = ok ? "rgba(124,107,81,0.15)" : "rgba(226,206,174,0.05)";
}

function showValidation(messages){
  const box = $("validationBox");
  if (!messages || messages.length === 0){
    box.innerHTML = '<div class="okText">Проверка: ошибок нет.</div>';
    return;
  }
  box.innerHTML = '<div class="errorText">Проверка: ' + messages.length + ' ошибка(и):</div>' +
    '<ul class="small" style="margin:6px 0 0 18px;">' +
    messages.map(m => '<li>' + escapeXml(m) + '</li>').join("") +
    '</ul>';
}

function downloadText(filename, text){
  const blob = new Blob([text], {type: "application/xml;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// =========================
// Required rules (used for highlight + fill-progress)
// =========================
const REQUIRED = [
  { key:"ObjectName",  type:"text",  mode:"manual", el:"ObjectName" },
  { key:"Address",     type:"text",  mode:"manual", el:"Address" },
  { key:"ProjectOrganization", type:"text", mode:"manual", el:"ProjectOrganization" },
  { key:"ProjectTeamLead", type:"text", mode:"manual", el:"ProjectTeamLead" },
  { key:"ProjectTeam", type:"list", mode:"manual", list:"ProjectTeam" },
  { key:"WorkTypes",   type:"select",mode:"manual", el:"WorkTypes" },
  { key:"FunctionalPurposes", type:"list", mode:"manual", list:"FunctionalPurposes" },
  { key:"BuildingHeight", type:"decimal", mode:"manual", el:"BuildingHeight" },
  { key:"Area", type:"decimal", mode:"manual", el:"Area" },
  { key:"TotalFloorArea", type:"decimal", mode:"manual", el:"TotalFloorArea" },
  { key:"ApartmentsCount", type:"posint", mode:"manual", el:"ApartmentsCount" },
  { key:"ObjectHeight", type:"decimal", mode:"manual", el:"ObjectHeight" },
  { key:"FloorsCount", type:"posint", mode:"manual", el:"FloorsCount" },

  // IFC preview required fields
  { key:"ObjectName",  type:"text",  mode:"ifc", el:"ifc_ObjectName" },
  { key:"Address",     type:"text",  mode:"ifc", el:"ifc_Address" },
  { key:"ProjectOrganization", type:"text", mode:"ifc", el:"ifc_ProjectOrganization" },
  { key:"ProjectTeamLead", type:"text", mode:"ifc", el:"ifc_ProjectTeamLead" },
  { key:"BuildingHeight", type:"decimal", mode:"ifc", el:"ifc_BuildingHeight" },
  { key:"Area", type:"decimal", mode:"ifc", el:"ifc_Area" },
  { key:"TotalFloorArea", type:"decimal", mode:"ifc", el:"ifc_TotalFloorArea" },
  { key:"ApartmentsCount", type:"posint", mode:"ifc", el:"ifc_ApartmentsCount" },
  { key:"ObjectHeight", type:"decimal", mode:"ifc", el:"ifc_ObjectHeight" },
  { key:"FloorsCount", type:"posint", mode:"ifc", el:"ifc_FloorsCount" }
];

function isValidRequired(rule){
  if (rule.type === "list"){
    const vals = lists?.[rule.list]?.getValues?.() || [];
    return vals.length > 0;
  }
  const el = $(rule.el);
  if (!el) return false;
  const v = el.value;

  if (rule.type === "text") return isNonEmpty(v);
  if (rule.type === "select") return isNonEmpty(v);
  if (rule.type === "decimal") return toDecimalOrNull(v) !== null;
  if (rule.type === "posint") return toPosIntOrNull(v) !== null;

  return false;
}

function markInvalids(mode){
  document.querySelectorAll(".is-invalid").forEach(n => n.classList.remove("is-invalid"));

  const rules = REQUIRED.filter(r => r.mode === mode);
  for (const r of rules){
    if (r.type === "list") continue;
    const el = $(r.el);
    if (!el) continue;
    if (!isValidRequired(r)) el.classList.add("is-invalid");
  }
}

function updateFillProgress(){
  // Для вкладки проверки XML прогресс не нужен — оставляем как было, считаем по активной "manual/ifc"
  const mode = $("tabIfc").classList.contains("active") ? "ifc" : "manual";
  const rules = REQUIRED.filter(r => r.mode === mode);

  let done = 0;
  for (const r of rules){
    if (isValidRequired(r)) done++;
  }
  const total = rules.length;
  const pct = total ? Math.round(done / total * 100) : 0;

  $("fillCount").textContent = `${done}/${total}`;
  $("fillPercent").textContent = `${pct}%`;
  $("barFill").style.width = `${pct}%`;

  if ($("tabXmlCheck").classList.contains("active")){
    $("fillHint").textContent = "Вкладка «Проверка XML»: прогресс заполнения относится к генерации (ручной ввод / IFC).";
    return;
  }

  if (pct === 100){
    $("fillHint").textContent = "Все обязательные параметры заполнены — можно генерировать XML.";
  } else {
    $("fillHint").textContent = "Заполняйте обязательные поля (выделены). Прогресс обновляется автоматически.";
  }
}

// =========================
// Repeatable lists builder
// =========================
function makeRepeatList(containerId, title, itemLabel, itemKey, purposeText, required=false){
  const c = $(containerId);
  c.innerHTML = `
    <div class="section">
      <div class="section-h">
        <div class="name">${escapeXml(title)}${required ? ' <span class="reqMark">обязательно</span>' : ''}</div>
        <div class="hint">${escapeXml(itemLabel)} (можно несколько)<br>${escapeXml(purposeText || "")}</div>
      </div>
      <div class="list" id="${containerId}_items"></div>
      <div style="padding: 0 12px 12px;">
        <button class="ghost" type="button" id="${containerId}_add">+ Добавить</button>
      </div>
    </div>
  `;

  const items = $(containerId + "_items");
  const addBtn = $(containerId + "_add");

  function addItem(value=""){
    const id = safeUUID();
    const el = document.createElement("div");
    el.className = "listItem";
    el.dataset.itemid = id;
    el.innerHTML = `
      <div>
        <label>${escapeXml(itemLabel)}${required ? '<span class="reqMark">обязательно</span>' : ''}</label>
        <input type="text" class="${required ? 'is-required' : ''}" data-key="${escapeXml(itemKey)}" value="${escapeXml(value)}" />
        <div class="help"><span class="k">Параметр:</span>${escapeXml(purposeText || "повторяющееся значение.")}</div>
      </div>
      <div class="actions">
        <button class="ghost" type="button" data-remove="${id}">Удалить</button>
      </div>
    `;
    items.appendChild(el);
    el.querySelector(`[data-remove="${id}"]`).addEventListener("click", () => {
      el.remove();
      updateFillProgress();
    });
    el.querySelector(`input[data-key="${itemKey}"]`).addEventListener("input", updateFillProgress);
  }

  addBtn.addEventListener("click", () => { addItem(); updateFillProgress(); });

  return {
    addItem,
    getValues: () => Array.from(items.querySelectorAll(`input[data-key="${itemKey}"]`))
      .map(i => i.value.trim()).filter(v => v !== "")
  };
}

const lists = {};

function initLists(){
  lists.CadastralNumbers = makeRepeatList("list_CadastralNumbers","CadastralNumbers","CadastralNumber","CadastralNumber","кадастровый номер участка/объекта.");
  lists.GPZUNumbers = makeRepeatList("list_GPZUNumbers","GPZUNumbers","GPZUNumber","GPZUNumber","номер(а) ГПЗУ.");
  lists.PPTNumbers = makeRepeatList("list_PPTNumbers","PPTNumbers","PPTNumber","PPTNumber","номер(а) ППТ.");
  lists.GZKDecisionNumbers = makeRepeatList("list_GZKDecisionNumbers","GZKDecisionNumbers","GZKDecisionNumber","GZKDecisionNumber","номер(а) решений ГЗК.");
  lists.KRTNumbers = makeRepeatList("list_KRTNumbers","KRTNumbers","KRTNumber","KRTNumber","номер(а) КРТ.");
  lists.PPMNumbers = makeRepeatList("list_PPMNumbers","PPMNumbers","PPMNumber","PPMNumber","номер(а) ППМ.");

  lists.ProjectTeam = makeRepeatList("list_ProjectTeam","ProjectTeam","Member","Member","участник проектной команды (ФИО).", true);
  lists.FunctionalPurposes = makeRepeatList("list_FunctionalPurposes","FunctionalPurposes","FunctionalPurpose","FunctionalPurpose","функциональное назначение объекта/части.", true);

  lists.ProjectTeam.addItem("");
  lists.FunctionalPurposes.addItem("");
}

// =========================
// XML generation (no schemaLocation in XML)
// =========================
function buildXml(data){
  const errors = [];

  if (!isNonEmpty(data.ObjectName)) errors.push("ObjectName обязателен.");
  if (!isNonEmpty(data.Address)) errors.push("Address обязателен.");
  if (!isNonEmpty(data.ProjectOrganization)) errors.push("ProjectOrganization обязателен.");
  if (!isNonEmpty(data.ProjectTeamLead)) errors.push("ProjectTeamLead обязателен.");
  if (!data.ProjectTeam || data.ProjectTeam.length === 0) errors.push("ProjectTeam должен содержать хотя бы одного участника (Member).");
  if (!isNonEmpty(data.WorkTypes)) errors.push("WorkTypes обязателен.");
  if (!data.FunctionalPurposes || data.FunctionalPurposes.length === 0) errors.push("FunctionalPurposes должен содержать хотя бы одно значение.");

  const reqDec = ["BuildingHeight","Area","TotalFloorArea","ObjectHeight"];
  reqDec.forEach(k => {
    if (toDecimalOrNull(data[k]) === null) errors.push(`${k} обязателен и должен быть числом.`);
  });

  const reqInt = ["ApartmentsCount","FloorsCount"];
  reqInt.forEach(k => {
    if (toPosIntOrNull(data[k]) === null) errors.push(`${k} обязателен и должен быть положительным целым.`);
  });

  if (isNonEmpty(data.Date)){
    const s = String(data.Date).trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) errors.push("Date должен быть в формате YYYY-MM-DD.");
  }

  showValidation(errors);
  if (errors.length) return { xml: "", ok: false };

  const xsi = `xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"`;

  let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
  xml += `<ArchitecturalUrbanPlanningSolution ${xsi}>\n`;

  xml += `\t<ObjectName>${escapeXml(data.ObjectName)}</ObjectName>\n`;
  if (isNonEmpty(data.RegistrationNumber)) xml += `\t<RegistrationNumber>${escapeXml(data.RegistrationNumber)}</RegistrationNumber>\n`;
  if (isNonEmpty(data.Date)) xml += `\t<Date>${escapeXml(data.Date)}</Date>\n`;
  xml += `\t<Address>${escapeXml(data.Address)}</Address>\n`;

  function addListBlock(containerName, itemName, values){
    if (!values || values.length === 0) return;
    xml += `\t<${containerName}>\n`;
    values.forEach(v => xml += `\t\t<${itemName}>${escapeXml(v)}</${itemName}>\n`);
    xml += `\t</${containerName}>\n`;
  }

  addListBlock("CadastralNumbers","CadastralNumber", data.CadastralNumbers);
  addListBlock("GPZUNumbers","GPZUNumber", data.GPZUNumbers);
  addListBlock("PPTNumbers","PPTNumber", data.PPTNumbers);
  addListBlock("GZKDecisionNumbers","GZKDecisionNumber", data.GZKDecisionNumbers);
  addListBlock("KRTNumbers","KRTNumber", data.KRTNumbers);
  addListBlock("PPMNumbers","PPMNumber", data.PPMNumbers);

  if (isNonEmpty(data.UUID)) xml += `\t<UUID>${escapeXml(data.UUID)}</UUID>\n`;

  xml += `\t<ProjectOrganization>${escapeXml(data.ProjectOrganization)}</ProjectOrganization>\n`;
  xml += `\t<ProjectTeamLead>${escapeXml(data.ProjectTeamLead)}</ProjectTeamLead>\n`;
  xml += `\t<ProjectTeam>\n`;
  data.ProjectTeam.forEach(m => xml += `\t\t<Member>${escapeXml(m)}</Member>\n`);
  xml += `\t</ProjectTeam>\n`;

  xml += `\t<WorkTypes>${escapeXml(data.WorkTypes)}</WorkTypes>\n`;

  xml += `\t<FunctionalPurposes>\n`;
  data.FunctionalPurposes.forEach(fp => xml += `\t\t<FunctionalPurpose>${escapeXml(fp)}</FunctionalPurpose>\n`);
  xml += `\t</FunctionalPurposes>\n`;

  const optDec = [
    "ResidentialPartArea","ResidentialPartOfResidentialArea","NonResidentialPartOfResidentialArea","NonResidentialObjectsArea",
    "TotalObjectArea","AboveGroundArea","UndergroundArea","NonResidentialAboveGroundAreaNonResidentialPart",
    "NonResidentialAboveGroundAreaNonResidentialObjects","ApartmentsAreaExSummerPremises","GreenArea",
    "ChildrenPlaygroundArea","RecreationsArea","ApartmentsArea","TotalApartmentsArea"
  ];
  const optInt = ["InformationStructuresCount"];

  xml += `\t<BuildingHeight>${fmtDecimal(data.BuildingHeight)}</BuildingHeight>\n`;
  xml += `\t<Area>${fmtDecimal(data.Area)}</Area>\n`;
  xml += `\t<TotalFloorArea>${fmtDecimal(data.TotalFloorArea)}</TotalFloorArea>\n`;

  optDec.forEach(k => {
    const n = toDecimalOrNull(data[k]);
    if (n !== null) xml += `\t<${k}>${fmtDecimal(n)}</${k}>\n`;
  });

  xml += `\t<ApartmentsCount>${toPosIntOrNull(data.ApartmentsCount)}</ApartmentsCount>\n`;

  xml += `\t<ObjectHeight>${fmtDecimal(data.ObjectHeight)}</ObjectHeight>\n`;
  xml += `\t<FloorsCount>${toPosIntOrNull(data.FloorsCount)}</FloorsCount>\n`;

  optInt.forEach(k => {
    const n = toPosIntOrNull(data[k]);
    if (n !== null) xml += `\t<${k}>${n}</${k}>\n`;
  });
  if (isNonEmpty(data.InformationStructuresParameters)) {
    xml += `\t<InformationStructuresParameters>${escapeXml(data.InformationStructuresParameters)}</InformationStructuresParameters>\n`;
  }

  xml += `</ArchitecturalUrbanPlanningSolution>\n`;

  // подпись
  xml = addSignatureCommentToXml(xml);

  return { xml, ok: true };
}

function collectManualData(){
  return {
    ObjectName: $("ObjectName").value,
    RegistrationNumber: $("RegistrationNumber").value,
    Date: $("Date").value,
    Address: $("Address").value,

    CadastralNumbers: lists.CadastralNumbers.getValues(),
    GPZUNumbers: lists.GPZUNumbers.getValues(),
    PPTNumbers: lists.PPTNumbers.getValues(),
    GZKDecisionNumbers: lists.GZKDecisionNumbers.getValues(),
    KRTNumbers: lists.KRTNumbers.getValues(),
    PPMNumbers: lists.PPMNumbers.getValues(),

    UUID: $("UUID").value,

    ProjectOrganization: $("ProjectOrganization").value,
    ProjectTeamLead: $("ProjectTeamLead").value,
    ProjectTeam: lists.ProjectTeam.getValues(),

    WorkTypes: $("WorkTypes").value,
    FunctionalPurposes: lists.FunctionalPurposes.getValues(),

    BuildingHeight: $("BuildingHeight").value,
    Area: $("Area").value,
    TotalFloorArea: $("TotalFloorArea").value,

    ResidentialPartArea: $("ResidentialPartArea").value,
    ResidentialPartOfResidentialArea: $("ResidentialPartOfResidentialArea").value,
    NonResidentialPartOfResidentialArea: $("NonResidentialPartOfResidentialArea").value,
    NonResidentialObjectsArea: $("NonResidentialObjectsArea").value,
    TotalObjectArea: $("TotalObjectArea").value,
    AboveGroundArea: $("AboveGroundArea").value,
    UndergroundArea: $("UndergroundArea").value,
    NonResidentialAboveGroundAreaNonResidentialPart: $("NonResidentialAboveGroundAreaNonResidentialPart").value,
    NonResidentialAboveGroundAreaNonResidentialObjects: $("NonResidentialAboveGroundAreaNonResidentialObjects").value,
    ApartmentsAreaExSummerPremises: $("ApartmentsAreaExSummerPremises").value,
    ApartmentsCount: $("ApartmentsCount").value,
    GreenArea: $("GreenArea").value,
    ChildrenPlaygroundArea: $("ChildrenPlaygroundArea").value,
    RecreationsArea: $("RecreationsArea").value,

    ObjectHeight: $("ObjectHeight").value,
    FloorsCount: $("FloorsCount").value,

    ApartmentsArea: $("ApartmentsArea").value,
    TotalApartmentsArea: $("TotalApartmentsArea").value,

    InformationStructuresCount: $("InformationStructuresCount").value,
    InformationStructuresParameters: $("InformationStructuresParameters").value
  };
}

// =========================
// Tabs (manual / ifc / xmlcheck / cimlist)
// =========================
function setTab(which){
  const isManual = which === "manual";
  const isIfc = which === "ifc";
  const isCheck = which === "xmlcheck";
  const isCim = which === "cimlist";

  // XML Check (ТЭП): правую панель скрываем полностью
  document.body.classList.toggle("hide-right-panel", isCheck);

  $("tabManual").classList.toggle("active", isManual);
  $("tabIfc").classList.toggle("active", isIfc);
  $("tabXmlCheck").classList.toggle("active", isCheck);
  $("tabCimArList").classList.toggle("active", isCim);

  $("panelManual").style.display = isManual ? "block" : "none";
  $("panelIfc").style.display = isIfc ? "block" : "none";
  $("panelXmlCheck").style.display = isCheck ? "block" : "none";
  $("panelCimArList").style.display = isCim ? "block" : "none";

  // переключение правой панели: ТЭП vs Список ЦИМ АР
  $("rightTepHead").style.display = isCim ? "none" : "flex";
  $("rightTepBody").style.display = isCim ? "none" : "block";
  $("rightCimHead").style.display = isCim ? "flex" : "none";
  $("rightCimBody").style.display = isCim ? "block" : "none";

  updateFillProgress();

  if (isManual) markInvalids("manual");
  if (isIfc) markInvalids("ifc");
}

// IFC availability check
function ifcAllowed(){
  return location.protocol !== "file:";
}

$("tabManual").addEventListener("click", () => setTab("manual"));

$("tabIfc").addEventListener("click", () => {
  if (!ifcAllowed()){
    $("ifcProtocolWarn").style.display = "block";
    $("tabIfc").classList.add("disabled");
    return;
  }
  $("ifcProtocolWarn").style.display = "none";
  $("tabIfc").classList.remove("disabled");
  setTab("ifc");
});

$("tabXmlCheck").addEventListener("click", () => {
  setTab("xmlcheck");
});

$("tabCimArList").addEventListener("click", () => {
  setTab("cimlist");
});

// =========================
// Manual actions
// =========================
function generateFromManual(){
  const data = collectManualData();
  const {xml, ok} = buildXml(data);
  $("xmlOut").value = xml;
  setXmlState(ok);
  $("manualStatus").textContent = ok ? "XML сформирован" : "Нужно исправить ошибки";
  markInvalids("manual");
  updateFillProgress();
}

$("btnGenerateManual").addEventListener("click", generateFromManual);

$("btnFillDemo").addEventListener("click", () => {
  $("ObjectName").value = 'Жилой комплекс "Примерный" с торговым центром';
  $("RegistrationNumber").value = "РН-2024-001";
  $("Date").value = "2024-01-15";
  $("Address").value = "г. Москва, ул. Примерная, д. 1";

  initLists();
  lists.CadastralNumbers.addItem("77:01:0001001:1234");
  lists.CadastralNumbers.addItem("77:01:0001001:1235");
  lists.GPZUNumbers.addItem("ГПЗУ-77-001-2023");
  lists.PPTNumbers.addItem("ППТ-77-001");
  lists.GZKDecisionNumbers.addItem("ГЗК-2023-0456");
  lists.KRTNumbers.addItem("КРТ-2024-001");
  lists.PPMNumbers.addItem("ППМ-77-001");

  $("UUID").value = "UID-77-2024-001";
  $("ProjectOrganization").value = 'ООО "Проектная организация "Архитектурные решения""';
  $("ProjectTeamLead").value = "Иванов Иван Иванович";

  const teamVals = ["Петров Петр Петрович","Сидоров Сидор Сидорович"];
  const teamItems = document.querySelectorAll('#list_ProjectTeam_items input[data-key="Member"]');
  if (teamItems[0]) teamItems[0].value = teamVals[0];
  for (let i=1;i<teamVals.length;i++) lists.ProjectTeam.addItem(teamVals[i]);

  $("WorkTypes").value = "новое строительство";

  const fps = ["многоквартирный жилой дом","торговый центр"];
  const fpItems = document.querySelectorAll('#list_FunctionalPurposes_items input[data-key="FunctionalPurpose"]');
  if (fpItems[0]) fpItems[0].value = fps[0];
  for (let i=1;i<fps.length;i++) lists.FunctionalPurposes.addItem(fps[i]);

  $("BuildingHeight").value = "15.5";
  $("Area").value = "1.25";
  $("TotalFloorArea").value = "25000.75";

  $("ResidentialPartArea").value = "18000.50";
  $("ResidentialPartOfResidentialArea").value = "16500.25";
  $("NonResidentialPartOfResidentialArea").value = "1500.25";
  $("NonResidentialObjectsArea").value = "7000.25";

  $("TotalObjectArea").value = "30000.75";
  $("AboveGroundArea").value = "22000.00";
  $("UndergroundArea").value = "8000.75";

  $("NonResidentialAboveGroundAreaNonResidentialPart").value = "2000.50";
  $("NonResidentialAboveGroundAreaNonResidentialObjects").value = "5000.00";

  $("TotalApartmentsArea").value = "16000.00";
  $("ApartmentsAreaExSummerPremises").value = "16000.00";

  $("ApartmentsCount").value = "200";
  $("ObjectHeight").value = "75.5";
  $("FloorsCount").value = "20";

  $("GreenArea").value = "3500.00";
  $("ChildrenPlaygroundArea").value = "500.00";
  $("RecreationsArea").value = "300.00";

  $("manualStatus").textContent = "Демо заполнено";
  setTab("manual");
  updateFillProgress();
  markInvalids("manual");
});

// =========================
// Preview actions
// =========================
$("btnDownload").addEventListener("click", () => {
  let xml = $("xmlOut").value || "";
  if (!xml.trim()) return;
  xml = addSignatureCommentToXml(xml); // на всякий случай
  downloadText("agr_tep.xml", xml);
});

$("btnCopyXml").addEventListener("click", async () => {
  let xml = $("xmlOut").value || "";
  if (!xml.trim()) return;
  xml = addSignatureCommentToXml(xml);
  try{
    await navigator.clipboard.writeText(xml);
    $("xmlState").textContent = "XML скопирован";
    setTimeout(() => $("xmlState").textContent = "XML сформирован", 900);
  }catch(e){
    alert("Не удалось скопировать (ограничения браузера).");
  }
});

$("btnGenerateTop").addEventListener("click", () => {
  const manualActive = $("tabManual").classList.contains("active");
  const ifcActive = $("tabIfc").classList.contains("active");

  if (manualActive) generateFromManual();
  else if (ifcActive) $("btnGenerateFromIfc").click();
  else {
    // вкладка проверки XML — ничего не генерируем
    $("xmlState").textContent = "Вы на вкладке проверки XML";
    setTimeout(() => $("xmlState").textContent = "XML не сформирован", 900);
  }
});

// Отдельная кнопка в правой панели для вкладки «Список ЦИМ АР»
$("btnGenerateCimTop").addEventListener("click", () => {
  if ($("tabCimArList").classList.contains("active")) {
    $("btnCimGenerate").click();
  }
});

// Live fill-progress updates
function wireLiveUpdates(){
  const ids = [
    "ObjectName","Address","ProjectOrganization","ProjectTeamLead","WorkTypes",
    "BuildingHeight","Area","TotalFloorArea","ApartmentsCount","ObjectHeight","FloorsCount",
    "ifc_ObjectName","ifc_Address","ifc_ProjectOrganization","ifc_ProjectTeamLead",
    "ifc_BuildingHeight","ifc_Area","ifc_TotalFloorArea","ifc_ApartmentsCount","ifc_ObjectHeight","ifc_FloorsCount"
  ];
  ids.forEach(id => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("input", () => {
      updateFillProgress();
      const mode = $("tabIfc").classList.contains("active") ? "ifc" : "manual";
      if (!$("tabXmlCheck").classList.contains("active")) markInvalids(mode);
    });
    el.addEventListener("change", () => {
      updateFillProgress();
      const mode = $("tabIfc").classList.contains("active") ? "ifc" : "manual";
      if (!$("tabXmlCheck").classList.contains("active")) markInvalids(mode);
    });
  });
}

/* ---------------------------------------------------------
   IFC parsing (web-ifc)
   ... (блок без изменений — оставлен как у тебя)
--------------------------------------------------------- */

/* ---------------------------------------------------------
   XML CHECK TAB wiring
   ... (блок без изменений — оставлен как у тебя)
--------------------------------------------------------- */

/* ---------------------------------------------------------
   NEW: Syntax + structure validation with line numbers
   ... (блок без изменений — оставлен как у тебя)
--------------------------------------------------------- */

/* ---------------------------------------------------------
   XML CHECK TAB wiring
   ... (блок без изменений — оставлен как у тебя)
--------------------------------------------------------- */

// =========================
// CIM AR LIST TAB (separate XML)
// =========================
const CIM_REQUIRED = ["Number","CIMName","CIMDescription","Section"];

let cimRows = [
  { Number: "1", CIMName: "", CIMDescription: "", Section: "" }
];

function cimEscape(s){ return escapeXml(s); }

function cimSetState(ok){
  $("cimXmlState").textContent = ok ? "✔️ XML списка сформирован" : "❌ XML списка не сформирован";
  $("btnCimDownload").disabled = !ok;
  $("btnCimCopyXml").disabled = !ok;
  $("cimXmlState").style.borderColor = ok ? "rgba(124,107,81,0.55)" : "rgba(226,206,174,0.22)";
  $("cimXmlState").style.background = ok ? "rgba(124,107,81,0.15)" : "rgba(226,206,174,0.05)";
}

function cimRenderTable(){
  const body = $("cimTableBody");
  body.innerHTML = "";

  cimRows.forEach((r, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="number" min="1" step="1" data-k="Number" data-i="${idx}" value="${cimEscape(r.Number)}" class="is-required"/></td>
      <td><input type="text" data-k="CIMName" data-i="${idx}" value="${cimEscape(r.CIMName)}" class="is-required" placeholder="Напр.: AR_Model.ifc"/></td>
      <td><input type="text" data-k="CIMDescription" data-i="${idx}" value="${cimEscape(r.CIMDescription)}" class="is-required" placeholder="Краткое описание"/></td>
      <td><input type="text" data-k="Section" data-i="${idx}" value="${cimEscape(r.Section)}" class="is-required" placeholder="Раздел по ПП РФ №87"/></td>
    `;
    body.appendChild(tr);
  });

  body.querySelectorAll("input").forEach(inp => {
    inp.addEventListener("input", (e) => {
      const i = Number(e.target.dataset.i);
      const k = e.target.dataset.k;
      cimRows[i][k] = e.target.value;
    });
  });
}

function cimValidateRows(){
  const errors = [];
  const nums = new Set();

  cimRows.forEach((r, idx) => {
    const rowN = idx + 1;
    const n = toPosIntOrNull(r.Number);
    if (n === null) errors.push(`Строка ${rowN}: № п.п. должен быть положительным целым.`);
    else {
      if (nums.has(n)) errors.push(`Строка ${rowN}: повторяющийся № п.п. (${n}).`);
      nums.add(n);
    }

    if (!isNonEmpty(r.CIMName)) errors.push(`Строка ${rowN}: «Наименование ЦИМ АГР» пустое.`);
    if (!isNonEmpty(r.CIMDescription)) errors.push(`Строка ${rowN}: «Описание ЦИМ АГР» пустое.`);
    if (!isNonEmpty(r.Section)) errors.push(`Строка ${rowN}: «Раздел» пустой.`);
  });

  return errors;
}

function cimBuildXml(){
  const errors = cimValidateRows();
  if (errors.length){
    $("cimManualStatus").textContent = "Нужно исправить ошибки";
    $("cimXmlOut").value = "";
    cimSetState(false);
    alert("Ошибки:\n" + errors.join("\n"));
    return { ok:false, xml:"" };
  }

  const createdAt = new Date().toISOString().slice(0,10);

  let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
  xml += `<CIMAGRFileList>\n`;
  xml += `\t<Files>\n`;
  cimRows.forEach(r => {
    xml += `\t\t<File>\n`;
    xml += `\t\t\t<Number>${cimEscape(String(toPosIntOrNull(r.Number)))}</Number>\n`;
    xml += `\t\t\t<CIMName>${cimEscape(r.CIMName)}</CIMName>\n`;
    xml += `\t\t\t<CIMDescription>${cimEscape(r.CIMDescription)}</CIMDescription>\n`;
    xml += `\t\t\t<Section>${cimEscape(r.Section)}</Section>\n`;
    xml += `\t\t</File>\n`;
  });
  xml += `\t</Files>\n`;
  xml += `\t<Meta>\n`;
  xml += `\t\t<CreatedBy>Marichev Alexey</CreatedBy>\n`;
  xml += `\t\t<Source>https://t.me/SMailsPub</Source>\n`;
  xml += `\t\t<CreatedAt>${createdAt}</CreatedAt>\n`;
  xml += `\t</Meta>\n`;
  xml += `</CIMAGRFileList>\n`;

  return { ok:true, xml };
}

function cimGenerate(){
  const {ok, xml} = cimBuildXml();
  $("cimXmlOut").value = xml;
  cimSetState(ok);
  $("cimManualStatus").textContent = ok ? "XML сформирован" : "Ожидание";
}

$("btnCimAddRow").addEventListener("click", () => {
  cimRows.push({ Number: String(cimRows.length + 1), CIMName:"", CIMDescription:"", Section:"" });
  cimRenderTable();
});

$("btnCimRemoveRow").addEventListener("click", () => {
  if (cimRows.length <= 1) return;
  cimRows.pop();
  cimRenderTable();
});

$("btnCimGenerate").addEventListener("click", cimGenerate);

$("btnCimDownload").addEventListener("click", () => {
  const xml = $("cimXmlOut").value || "";
  if (!xml.trim()) return;
  downloadText("cim_agr_list.xml", xml);
});

$("btnCimCopyXml").addEventListener("click", async () => {
  const xml = $("cimXmlOut").value || "";
  if (!xml.trim()) return;
  try{
    await navigator.clipboard.writeText(xml);
    $("cimXmlState").textContent = "XML списка скопирован";
    setTimeout(() => $("cimXmlState").textContent = "✔️ XML списка сформирован", 900);
  }catch(e){
    alert("Не удалось скопировать (ограничения браузера).");
  }
});

// Sub-tabs inside CIM tab
function setCimSubTab(which){
  const isM = which === "manual";
  $("subTabCimManual").classList.toggle("active", isM);
  $("subTabCimCheck").classList.toggle("active", !isM);
  $("cimPanelManual").style.display = isM ? "block" : "none";
  $("cimPanelCheck").style.display = isM ? "none" : "block";
}

$("subTabCimManual").addEventListener("click", () => setCimSubTab("manual"));
$("subTabCimCheck").addEventListener("click", () => setCimSubTab("check"));

// CIM XML check/fix
let lastCimDoc = null;
let lastCimFileName = "data.xml";
let lastCimParsable = false;

function cimGetRoot(doc){ return doc && doc.documentElement ? doc.documentElement : null; }

function cimFindDirect(parent, name){
  for (const n of parent.childNodes){
    if (n.nodeType === 1 && n.nodeName === name) return n;
  }
  return null;
}

function cimEnsureText(doc, parent, name, value){
  let el = cimFindDirect(parent, name);
  if (!el){
    el = doc.createElement(name);
    el.textContent = value;
    parent.appendChild(el);
    return el;
  }
  if (!isNonEmpty(el.textContent)) el.textContent = value;
  return el;
}

function cimCheckMinimal(doc){
  const errors = [];
  const root = cimGetRoot(doc);
  if (!root || root.nodeName !== "CIMAGRFileList"){
    errors.push({ path: "CIMAGRFileList", reason: "Отсутствует/неверный корневой элемент" });
    return errors;
  }

  const files = cimFindDirect(root, "Files");
  if (!files){
    errors.push({ path: "Files", reason: "Контейнер Files отсутствует" });
    return errors;
  }

  const fileEls = Array.from(files.childNodes).filter(n => n.nodeType === 1 && n.nodeName === "File");
  if (fileEls.length === 0){
    errors.push({ path: "Files/File", reason: "Нет ни одной строки File" });
    return errors;
  }

  fileEls.forEach((f, idx) => {
    const row = idx + 1;
    for (const tag of CIM_REQUIRED){
      const el = cimFindDirect(f, tag);
      if (!el) errors.push({ path: `File[${row}]/${tag}`, reason: "Элемент отсутствует" });
      else if (!isNonEmpty(el.textContent)) errors.push({ path: `File[${row}]/${tag}`, reason: "Пустое значение" });
    }
  });

  return errors;
}

function cimFixMinimal(doc){
  const root = cimGetRoot(doc);
  if (!root || root.nodeName !== "CIMAGRFileList") return doc;

  let files = cimFindDirect(root, "Files");
  if (!files){
    files = doc.createElement("Files");
    root.appendChild(doc.createTextNode("\n\t"));
    root.appendChild(files);
    root.appendChild(doc.createTextNode("\n"));
  }

  let fileEls = Array.from(files.childNodes).filter(n => n.nodeType === 1 && n.nodeName === "File");
  if (fileEls.length === 0){
    const f = doc.createElement("File");
    files.appendChild(doc.createTextNode("\n\t\t"));
    files.appendChild(f);
    files.appendChild(doc.createTextNode("\n\t"));
    fileEls = [f];
  }

  fileEls.forEach((f, idx) => {
    cimEnsureText(doc, f, "Number", String(idx + 1));
    cimEnsureText(doc, f, "CIMName", "НЕ_ЗАПОЛНЕНО");
    cimEnsureText(doc, f, "CIMDescription", "НЕ_ЗАПОЛНЕНО");
    cimEnsureText(doc, f, "Section", "НЕ_ЗАПОЛНЕНО");
  });

  let meta = cimFindDirect(root, "Meta");
  if (!meta){
    meta = doc.createElement("Meta");
    root.appendChild(doc.createTextNode("\n\t"));
    root.appendChild(meta);
    root.appendChild(doc.createTextNode("\n"));
  }
  const createdAt = new Date().toISOString().slice(0,10);
  cimEnsureText(doc, meta, "CreatedBy", "Marichev Alexey");
  cimEnsureText(doc, meta, "Source", "https://t.me/SMailsPub");
  cimEnsureText(doc, meta, "CreatedAt", createdAt);

  return doc;
}

function cimSerialize(doc){
  return new XMLSerializer().serializeToString(doc);
}

function initCimCheckTab(){
  const input = $("cimCheckFile");
  const btnCheck = $("btnCimCheck");
  const btnFix = $("btnCimFix");
  const report = $("cimCheckReport");
  const status = $("cimCheckStatus");

  if (!input || !btnCheck || !btnFix || !report || !status) return;

  btnCheck.addEventListener("click", async () => {
    status.textContent = "Проверка…";
    btnFix.disabled = true;
    report.textContent = "";
    lastCimDoc = null;
    lastCimParsable = false;

    const file = input.files?.[0];
    if (!file){
      status.textContent = "Ожидание";
      report.textContent = "Файл не выбран.";
      return;
    }
    lastCimFileName = file.name || "data.xml";

    const text = await readFileAsText(file);

    // синтаксис + структура тегов
    const v = validateXmlSyntaxAndStructure(text);
    if (!v.ok){
      lastCimParsable = false;
      status.textContent = "Ошибка синтаксиса/структуры";
      report.textContent =
        "Синтаксис XML некорректный или нарушена структура тегов.\n" +
        "Автоисправление недоступно (сначала нужно починить структуру файла).\n\n" +
        "Ошибки:\n" + renderXmlErrors(v.errors);
      return;
    }

    lastCimParsable = true;
    lastCimDoc = v.doc;

    const missing = cimCheckMinimal(lastCimDoc);
    if (missing.length === 0){
      status.textContent = "ОК";
      report.textContent =
        "ОК: синтаксис корректен.\n" +
        "Минимальная структура присутствует.\n\n" +
        "Можно нажать «Исправить и скачать», чтобы:\n" +
        "- заполнить пустые значения\n" +
        "- добавить Meta с подписью/ссылкой";
      btnFix.disabled = false;
      return;
    }

    status.textContent = `Проблем: ${missing.length}`;
    report.textContent =
      "Синтаксис корректен.\n\n" +
      "Найдены проблемы (минимальный набор):\n" +
      missing.map(x => `- ${x.path}: ${x.reason}`).join("\n") +
      "\n\nНажмите «Исправить и скачать» — добавлю недостающие элементы/значения и Meta.";
    btnFix.disabled = false;
  });

  btnFix.addEventListener("click", () => {
    if (!lastCimParsable || !lastCimDoc){
      status.textContent = "Нужно проверить XML";
      report.textContent = "Сначала нажмите «Проверить». Если синтаксис/структура битые — исправьте файл вручную.";
      return;
    }

    status.textContent = "Исправление…";

    const fixed = cimFixMinimal(lastCimDoc);
    const xml = cimSerialize(fixed);

    const base = lastCimFileName.replace(/\.xml$/i, "");
    downloadText(base + "_fixed.xml", xml);

    status.textContent = "Скачано";
    report.textContent += "\n\nСкачан файл: " + (base + "_fixed.xml");
  });
}

// =========================
// init
// =========================
initLists();
resetIfcUI();
setXmlState(false);
wireLiveUpdates();
initXmlCheckTab();
initCimCheckTab();

cimRenderTable();
cimSetState(false);
setCimSubTab("manual");

if (!ifcAllowed()){
  $("ifcProtocolWarn").style.display = "block";
  $("tabIfc").classList.add("disabled");
}

updateFillProgress();
markInvalids("manual");
