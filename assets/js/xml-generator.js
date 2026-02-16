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
// Tabs (manual / ifc / xmlcheck)
// =========================
function setTab(which){
  const isManual = which === "manual";
  const isIfc = which === "ifc";
  const isCheck = which === "xmlcheck";

  document.body.classList.toggle("hide-right-panel", isCheck);

  $("tabManual").classList.toggle("active", isManual);
  $("tabIfc").classList.toggle("active", isIfc);
  $("tabXmlCheck").classList.toggle("active", isCheck);

  $("panelManual").style.display = isManual ? "block" : "none";
  $("panelIfc").style.display = isIfc ? "block" : "none";
  $("panelXmlCheck").style.display = isCheck ? "block" : "none";

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

// =========================
// IFC parsing (web-ifc)
// =========================
let ifcApi = null;
let ifcModelId = null;
let ifcFlat = [];
let ifcKeyToValue = new Map();
let ifcHeuristic = {};

function setIfcError(msg){
  const box = $("ifcErrors");
  box.style.display = "block";
  box.textContent = msg;
}
function clearIfcError(){
  const box = $("ifcErrors");
  box.style.display = "none";
  box.textContent = "";
}

function setProgress(barId, labelId, pct){
  const p = Math.max(0, Math.min(100, pct));
  $(barId).style.width = p.toFixed(0) + "%";
  $(labelId).textContent = (labelId === "readLabel" ? "Чтение: " : "Парсинг: ") + p.toFixed(0) + "%";
}

function forceParse100(){
  setProgress("barParse","parseLabel",100);
  $("barParse").style.width = "100%";
  $("parseLabel").textContent = "Парсинг: 100%";
}

function resetIfcUI(){
  setProgress("barRead","readLabel",0);
  setProgress("barParse","parseLabel",0);
  $("ifcState").textContent = "IFC не загружен";
  $("ifcStatus").textContent = "Ожидание";
  $("mapStatus").textContent = "Сопоставление не применено";
  ifcFlat = [];
  ifcKeyToValue = new Map();
  ifcHeuristic = {};
  renderIfcTable();
  fillMappingSelects([]);
  updateFillProgress();
}

async function ensureIfcApi(){
  if (ifcApi) return ifcApi;
  const mod = await import("https://unpkg.com/web-ifc@0.0.57/web-ifc-api.js");
  const { IfcAPI } = mod;
  ifcApi = new IfcAPI();
  ifcApi.SetWasmPath("https://unpkg.com/web-ifc@0.0.57/");
  await ifcApi.Init();
  return ifcApi;
}

async function getPsetsForId(api, modelId, expressID){
  const lines = [];
  try{
    if (typeof api.GetLineIDsWithType !== "function") return lines;

    const REL_DEFINES = 4186316022; // IfcRelDefinesByProperties
    const rels = api.GetLineIDsWithType(modelId, REL_DEFINES);
    const size = rels.size();

    for (let i=0;i<size;i++){
      const relId = rels.get(i);
      const rel = api.GetLine(modelId, relId);
      if (!rel || !rel.RelatedObjects) continue;

      const related = rel.RelatedObjects;
      let hit = false;
      for (const ro of related){
        const rid = ro.value;
        if (rid === expressID){ hit = true; break; }
      }
      if (!hit) continue;

      const def = rel.RelatingPropertyDefinition;
      if (!def || !def.value) continue;
      const defLine = api.GetLine(modelId, def.value);
      if (!defLine) continue;

      if (defLine.HasProperties && defLine.Name){
        const psetName = defLine.Name.value || "Pset";
        for (const p of defLine.HasProperties){
          const propLine = api.GetLine(modelId, p.value);
          if (!propLine) continue;

          const propName = propLine.Name?.value || "Prop";
          let propVal = "";

          if (propLine.NominalValue && propLine.NominalValue.value !== undefined){
            propVal = String(propLine.NominalValue.value);
          } else if (propLine.Description?.value){
            propVal = String(propLine.Description.value);
          } else {
            try{ propVal = JSON.stringify(propLine); } catch(e){ propVal = String(propLine); }
          }

          lines.push({psetName, propName, propVal});
        }
      }

      if (defLine.Quantities && defLine.Name){
        const qsetName = defLine.Name.value || "Qto";
        for (const q of defLine.Quantities){
          const qLine = api.GetLine(modelId, q.value);
          if (!qLine) continue;
          const qName = qLine.Name?.value || "Quantity";
          let qVal = "";
          for (const k of Object.keys(qLine)){
            if (k.endsWith("Value") && qLine[k] && qLine[k].value !== undefined){
              qVal = String(qLine[k].value);
              break;
            }
          }
          if (!qVal && qLine.Description?.value) qVal = String(qLine.Description.value);
          lines.push({psetName: qsetName, propName: qName, propVal: qVal});
        }
      }
    }
  }catch(e){
    // ignore
  }
  return lines;
}

async function parseIfc(arrayBuffer){
  clearIfcError();
  $("ifcStatus").textContent = "Парсинг IFC…";
  $("ifcState").textContent = "IFC загружен, идёт парсинг";
  setProgress("barParse","parseLabel",3);

  const api = await ensureIfcApi();

  ifcModelId = api.OpenModel(new Uint8Array(arrayBuffer), {});
  setProgress("barParse","parseLabel",8);

  const TYPE = {
    IfcProject: 103090709,
    IfcSite: 4097777520,
    IfcBuilding: 4031249490
  };

  const targets = [];
  for (const [name, typeId] of Object.entries(TYPE)){
    const ids = api.GetLineIDsWithType(ifcModelId, typeId);
    const n = ids.size();
    for (let i=0;i<n;i++){
      targets.push({entity: name, id: ids.get(i)});
    }
  }

  ifcFlat = [];
  ifcKeyToValue = new Map();

  let processed = 0;
  const total = Math.max(1, targets.length);

  for (const t of targets){
    processed++;
    const pct = 8 + (processed/total) * 74;
    setProgress("barParse","parseLabel",pct);

    const line = api.GetLine(ifcModelId, t.id);
    if (!line) continue;

    const attrs = ["Name","LongName","Description","ObjectType"];
    for (const a of attrs){
      const v = line[a]?.value;
      if (v !== undefined && v !== null && String(v).trim() !== ""){
        const key = `${t.entity}::${a}`;
        ifcFlat.push({entity: t.entity, psetOrAttr: a, prop: a, value: String(v), key});
        ifcKeyToValue.set(key, String(v));
      }
    }

    const psets = await getPsetsForId(api, ifcModelId, t.id);
    for (const p of psets){
      const key = `${t.entity}::${p.psetName}::${p.propName}`;
      const val = (p.propVal ?? "").toString();
      ifcFlat.push({entity: t.entity, psetOrAttr: p.psetName, prop: p.propName, value: val, key});
      ifcKeyToValue.set(key, val);
    }
  }

  setProgress("barParse","parseLabel",90);

  ifcHeuristic = proposeFromIfc();
  applyIfcToPreview(ifcHeuristic);

  const keys = Array.from(ifcKeyToValue.keys()).sort((a,b)=>a.localeCompare(b));
  fillMappingSelects(keys);
  preselectMappingByHeuristics(keys);

  renderIfcTable();

  forceParse100();

  $("ifcStatus").textContent = "Парсинг завершён";
  $("ifcState").textContent = `IFC разобран: найдено записей ${ifcFlat.length}`;

  updateFillProgress();
  markInvalids("ifc");
}

function proposeFromIfc(){
  const priority = ["IfcBuilding","IfcSite","IfcProject"];

  function findByKeywords(keywords){
    for (const ent of priority){
      for (const row of ifcFlat){
        if (row.entity !== ent) continue;
        const hay = (row.psetOrAttr + " " + row.prop + " " + row.key).toLowerCase();
        for (const kw of keywords){
          if (hay.includes(kw)) return row.value;
        }
      }
    }
    for (const row of ifcFlat){
      const hay = (row.psetOrAttr + " " + row.prop + " " + row.key).toLowerCase();
      for (const kw of keywords){
        if (hay.includes(kw)) return row.value;
      }
    }
    return "";
  }

  const res = {};
  res.ObjectName = findByKeywords(["::name","::longname","building::name","project::name","наименование"]);
  res.Address = findByKeywords(["address","адрес","pset_address","siteaddress","p_siteaddress"]);
  res.ProjectOrganization = findByKeywords(["organization","организация","author","проектная","заказчик"]);
  res.ProjectTeamLead = findByKeywords(["lead","руковод","chief","гип","главный"]);
  res.TotalFloorArea = findByKeywords(["grossfloorarea","totalfloorarea","gross floor area","qto","floorarea","площад"]);
  res.Area = findByKeywords(["sitearea","land","plot","участ","земел","area"]);
  res.BuildingHeight = findByKeywords(["buildingheight","height","высот"]);
  res.ObjectHeight = findByKeywords(["overallheight","height","высот"]);
  res.FloorsCount = findByKeywords(["numberofstoreys","storey","floors","этаж","levels","level"]);
  res.ApartmentsCount = findByKeywords(["apartment","flat","квартир","units","dwelling","count"]);
  return res;
}

function applyIfcToPreview(obj){
  $("ifc_ObjectName").value = obj.ObjectName || "";
  $("ifc_Address").value = obj.Address || "";
  $("ifc_ProjectOrganization").value = obj.ProjectOrganization || "";
  $("ifc_ProjectTeamLead").value = obj.ProjectTeamLead || "";
  $("ifc_BuildingHeight").value = obj.BuildingHeight || "";
  $("ifc_Area").value = obj.Area || "";
  $("ifc_TotalFloorArea").value = obj.TotalFloorArea || "";
  $("ifc_ApartmentsCount").value = obj.ApartmentsCount || "";
  $("ifc_ObjectHeight").value = obj.ObjectHeight || "";
  $("ifc_FloorsCount").value = obj.FloorsCount || "";

  updateFillProgress();
  markInvalids("ifc");
}

function fillMappingSelects(keys){
  const mapIds = [
    "map_ObjectName","map_Address","map_ProjectOrganization","map_ProjectTeamLead",
    "map_BuildingHeight","map_Area","map_TotalFloorArea","map_ApartmentsCount","map_ObjectHeight","map_FloorsCount"
  ];
  for (const id of mapIds){
    const sel = $(id);
    sel.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "— не использовать —";
    sel.appendChild(opt0);
    for (const k of keys){
      const o = document.createElement("option");
      o.value = k;
      o.textContent = k;
      sel.appendChild(o);
    }
  }
}

function preselectMappingByHeuristics(keys){
  function pickByValue(val){
    if (!val) return "";
    for (const k of keys){
      const v = ifcKeyToValue.get(k);
      if (v === val) return k;
    }
    return "";
  }
  $("map_ObjectName").value = pickByValue(ifcHeuristic.ObjectName);
  $("map_Address").value = pickByValue(ifcHeuristic.Address);
  $("map_ProjectOrganization").value = pickByValue(ifcHeuristic.ProjectOrganization);
  $("map_ProjectTeamLead").value = pickByValue(ifcHeuristic.ProjectTeamLead);
  $("map_BuildingHeight").value = pickByValue(ifcHeuristic.BuildingHeight);
  $("map_Area").value = pickByValue(ifcHeuristic.Area);
  $("map_TotalFloorArea").value = pickByValue(ifcHeuristic.TotalFloorArea);
  $("map_ApartmentsCount").value = pickByValue(ifcHeuristic.ApartmentsCount);
  $("map_ObjectHeight").value = pickByValue(ifcHeuristic.ObjectHeight);
  $("map_FloorsCount").value = pickByValue(ifcHeuristic.FloorsCount);
}

$("btnApplyMapping").addEventListener("click", () => {
  const mapping = {
    ObjectName: $("map_ObjectName").value,
    Address: $("map_Address").value,
    ProjectOrganization: $("map_ProjectOrganization").value,
    ProjectTeamLead: $("map_ProjectTeamLead").value,
    BuildingHeight: $("map_BuildingHeight").value,
    Area: $("map_Area").value,
    TotalFloorArea: $("map_TotalFloorArea").value,
    ApartmentsCount: $("map_ApartmentsCount").value,
    ObjectHeight: $("map_ObjectHeight").value,
    FloorsCount: $("map_FloorsCount").value
  };
  const out = {};
  for (const [k, src] of Object.entries(mapping)){
    out[k] = src ? (ifcKeyToValue.get(src) || "") : ( $("ifc_"+k)?.value || "" );
  }
  applyIfcToPreview(out);
  $("mapStatus").textContent = "Сопоставление применено";
});

function collectIfcDataForXml(){
  return {
    ObjectName: $("ifc_ObjectName").value,
    Address: $("ifc_Address").value,
    ProjectOrganization: $("ifc_ProjectOrganization").value,
    ProjectTeamLead: $("ifc_ProjectTeamLead").value,
    BuildingHeight: $("ifc_BuildingHeight").value,
    Area: $("ifc_Area").value,
    TotalFloorArea: $("ifc_TotalFloorArea").value,
    ApartmentsCount: $("ifc_ApartmentsCount").value,
    ObjectHeight: $("ifc_ObjectHeight").value,
    FloorsCount: $("ifc_FloorsCount").value
  };
}

$("btnGenerateFromIfc").addEventListener("click", () => {
  const subset = collectIfcDataForXml();
  const base = collectManualData();

  base.ObjectName = subset.ObjectName;
  base.Address = subset.Address;
  base.ProjectOrganization = subset.ProjectOrganization;
  base.ProjectTeamLead = subset.ProjectTeamLead;
  base.BuildingHeight = subset.BuildingHeight;
  base.Area = subset.Area;
  base.TotalFloorArea = subset.TotalFloorArea;
  base.ApartmentsCount = subset.ApartmentsCount;
  base.ObjectHeight = subset.ObjectHeight;
  base.FloorsCount = subset.FloorsCount;

  const {xml, ok} = buildXml(base);
  $("xmlOut").value = xml;
  setXmlState(ok);
  $("ifcStatus").textContent = ok ? "XML сформирован" : "Нужно заполнить обязательные поля (часть берётся из ручного ввода: команда/назначение/вид работ)";
  markInvalids("ifc");
  updateFillProgress();
});

$("btnCopyIfcToManual").addEventListener("click", () => {
  const subset = collectIfcDataForXml();

  if (isNonEmpty(subset.ObjectName)) $("ObjectName").value = subset.ObjectName;
  if (isNonEmpty(subset.Address)) $("Address").value = subset.Address;
  if (isNonEmpty(subset.ProjectOrganization)) $("ProjectOrganization").value = subset.ProjectOrganization;
  if (isNonEmpty(subset.ProjectTeamLead)) $("ProjectTeamLead").value = subset.ProjectTeamLead;

  if (isNonEmpty(subset.BuildingHeight)) $("BuildingHeight").value = subset.BuildingHeight;
  if (isNonEmpty(subset.Area)) $("Area").value = subset.Area;
  if (isNonEmpty(subset.TotalFloorArea)) $("TotalFloorArea").value = subset.TotalFloorArea;
  if (isNonEmpty(subset.ApartmentsCount)) $("ApartmentsCount").value = subset.ApartmentsCount;
  if (isNonEmpty(subset.ObjectHeight)) $("ObjectHeight").value = subset.ObjectHeight;
  if (isNonEmpty(subset.FloorsCount)) $("FloorsCount").value = subset.FloorsCount;

  setTab("manual");
  $("manualStatus").textContent = "Значения перенесены из IFC";
  updateFillProgress();
  markInvalids("manual");
});

function renderIfcTable(){
  const body = $("ifcTableBody");
  const filter = ($("ifcFilter")?.value || "").trim().toLowerCase();
  const limit = Number($("ifcLimit")?.value || "200");

  body.innerHTML = "";
  if (!ifcFlat || ifcFlat.length === 0){
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="4" class="small">Нет данных. Загрузите IFC.</td>`;
    body.appendChild(tr);
    return;
  }

  let shown = 0;
  for (const row of ifcFlat){
    if (shown >= limit) break;
    const hay = (row.entity + " " + row.psetOrAttr + " " + row.prop + " " + row.value).toLowerCase();
    if (filter && !hay.includes(filter)) continue;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="mono">${escapeXml(row.entity)}</td>
      <td class="mono">${escapeXml(row.psetOrAttr)}</td>
      <td class="mono">${escapeXml(row.prop)}</td>
      <td>${escapeXml(row.value)}</td>
    `;
    body.appendChild(tr);
    shown++;
  }
  if (shown === 0){
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="4" class="small">Ничего не найдено по фильтру.</td>`;
    body.appendChild(tr);
  }
}

$("ifcFilter").addEventListener("input", renderIfcTable);
$("ifcLimit").addEventListener("change", renderIfcTable);

$("ifcFile").addEventListener("change", async (ev) => {
  resetIfcUI();
  clearIfcError();

  const file = ev.target.files?.[0];
  if (!file) return;

  if (!file.name.toLowerCase().endsWith(".ifc")){
    setIfcError("Нужен файл .ifc");
    return;
  }

  if (!ifcAllowed()){
    setIfcError("Открыто как file:// — IFC режим заблокирован. Откройте страницу через http://localhost (python -m http.server).");
    return;
  }

  $("ifcState").textContent = `Загрузка: ${file.name}`;
  $("ifcStatus").textContent = "Чтение файла…";

  const reader = new FileReader();
  reader.onprogress = (e) => {
    if (e.lengthComputable){
      const pct = (e.loaded / e.total) * 100;
      setProgress("barRead","readLabel",pct);
    }
  };
  reader.onerror = () => setIfcError("Ошибка чтения файла.");
  reader.onload = async () => {
    try{
      setProgress("barRead","readLabel",100);
      $("ifcStatus").textContent = "Файл прочитан";
      const buf = reader.result;
      await parseIfc(buf);
      $("ifcStatus").textContent = "Готово";
    }catch(e){
      console.error(e);
      setIfcError("Ошибка парсинга IFC. Проверьте запуск через HTTP и попробуйте другую модель/облегчённый IFC.");
      $("ifcStatus").textContent = "Ошибка";
      $("ifcState").textContent = "IFC не разобран";
    }
  };
  reader.readAsArrayBuffer(file);
});

// =========================
// XML CHECK TAB
//   1) синтаксис/well-formed + строки
//   2) минимально обязательные
//   3) исправление (только если синтаксис ОК)
// =========================
const MIN_REQUIRED_ORDER = [
  "ObjectName",
  "Address",
  "ProjectOrganization",
  "ProjectTeamLead",
  "ProjectTeam",
  "WorkTypes",
  "FunctionalPurposes",
  "BuildingHeight",
  "Area",
  "TotalFloorArea",
  "ApartmentsCount",
  "ObjectHeight",
  "FloorsCount"
];

const MIN_REQUIRED_DEFAULTS = {
  ObjectName: "НЕ_ЗАПОЛНЕНО",
  Address: "НЕ_ЗАПОЛНЕНО",
  ProjectOrganization: "НЕ_ЗАПОЛНЕНО",
  ProjectTeamLead: "НЕ_ЗАПОЛНЕНО",
  WorkTypes: "новое строительство",
  BuildingHeight: "0",
  Area: "0",
  TotalFloorArea: "0",
  ApartmentsCount: "1",
  ObjectHeight: "0",
  FloorsCount: "1"
};

let lastXmlDoc = null;
let lastXmlFileName = "data.xml";
let lastXmlIsParsable = false;

function readFileAsText(file){
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result || ""));
    r.onerror = reject;
    r.readAsText(file, "UTF-8");
  });
}

function getRoot(doc){
  return doc && doc.documentElement ? doc.documentElement : null;
}

function findDirectChild(parent, name){
  for (const n of parent.childNodes){
    if (n.nodeType === 1 && n.nodeName === name) return n;
  }
  return null;
}

function ensureChildText(doc, parent, childName, value){
  let ch = findDirectChild(parent, childName);
  if (!ch){
    ch = doc.createElement(childName);
    ch.textContent = value;
    parent.appendChild(ch);
    return;
  }
  if (!isNonEmpty(ch.textContent)) ch.textContent = value;
}

function ensureSignatureCommentInDoc(doc){
  const root = getRoot(doc);
  if (!root) return;

  const it = doc.createNodeIterator(doc, NodeFilter.SHOW_COMMENT);
  let n;
  while ((n = it.nextNode())){
    if ((n.nodeValue || "").includes("t.me/SMailsPub")) return;
  }

  root.appendChild(doc.createTextNode("\n\t"));
  root.appendChild(doc.createComment(" " + SIGNATURE_COMMENT + " "));
  root.appendChild(doc.createTextNode("\n"));
}

function checkMinimalMissing(doc){
  const miss = [];
  const root = getRoot(doc);

  if (!root || root.nodeName !== "ArchitecturalUrbanPlanningSolution"){
    miss.push({ path: "ArchitecturalUrbanPlanningSolution", reason: "Отсутствует/неверный корневой элемент" });
    return miss;
  }

  for (const name of MIN_REQUIRED_ORDER){
    const el = findDirectChild(root, name);
    if (!el){
      miss.push({ path: name, reason: "Элемент отсутствует" });
      continue;
    }

    if (name === "ProjectTeam"){
      const mem = findDirectChild(el, "Member");
      if (!mem || !isNonEmpty(mem.textContent)) miss.push({ path: "ProjectTeam/Member", reason: "Нет хотя бы одного Member" });
      continue;
    }

    if (name === "FunctionalPurposes"){
      const fp = findDirectChild(el, "FunctionalPurpose");
      if (!fp || !isNonEmpty(fp.textContent)) miss.push({ path: "FunctionalPurposes/FunctionalPurpose", reason: "Нет хотя бы одного FunctionalPurpose" });
      continue;
    }

    if (!isNonEmpty(el.textContent)) miss.push({ path: name, reason: "Пустое значение" });
  }

  return miss;
}

function insertInOrder(root, newName, newEl){
  const idx = MIN_REQUIRED_ORDER.indexOf(newName);
  if (idx === -1){
    root.appendChild(newEl);
    return;
  }
  for (let i = idx + 1; i < MIN_REQUIRED_ORDER.length; i++){
    const next = findDirectChild(root, MIN_REQUIRED_ORDER[i]);
    if (next){
      root.insertBefore(newEl, next);
      return;
    }
  }
  root.appendChild(newEl);
}

function fixMinimal(doc){
  const root = getRoot(doc);
  if (!root || root.nodeName !== "ArchitecturalUrbanPlanningSolution") return doc;

  for (const name of MIN_REQUIRED_ORDER){
    let el = findDirectChild(root, name);

    if (!el){
      el = doc.createElement(name);

      if (name === "ProjectTeam"){
        ensureChildText(doc, el, "Member", "НЕ_ЗАПОЛНЕНО");
      } else if (name === "FunctionalPurposes"){
        ensureChildText(doc, el, "FunctionalPurpose", "НЕ_ЗАПОЛНЕНО");
      } else {
        el.textContent = MIN_REQUIRED_DEFAULTS[name] ?? "НЕ_ЗАПОЛНЕНО";
      }

      insertInOrder(root, name, el);
    } else {
      if (name === "ProjectTeam"){
        ensureChildText(doc, el, "Member", "НЕ_ЗАПОЛНЕНО");
      } else if (name === "FunctionalPurposes"){
        ensureChildText(doc, el, "FunctionalPurpose", "НЕ_ЗАПОЛНЕНО");
      } else {
        if (!isNonEmpty(el.textContent)) el.textContent = MIN_REQUIRED_DEFAULTS[name] ?? "НЕ_ЗАПОЛНЕНО";
      }
    }
  }

  ensureSignatureCommentInDoc(doc);
  return doc;
}

function serializeXmlDoc(doc){
  const xml = new XMLSerializer().serializeToString(doc);
  return addSignatureCommentToXml(xml);
}

/* ---------------------------------------------------------
   NEW: Syntax + structure validation with line numbers
--------------------------------------------------------- */
function parseXmlWithDetails(xmlText){
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlText, "application/xml");
  const errorNode = doc.querySelector("parsererror");

  if (!errorNode) return { ok: true, doc, errors: [] };

  const raw = (errorNode.textContent || "XML синтаксис некорректен").trim();

  // Попытка вытащить line/column из сообщения (не гарантируется всеми браузерами)
  const lineMatch = raw.match(/line\s+(\d+)/i);
  const colMatch  = raw.match(/column\s+(\d+)/i);

  return {
    ok: false,
    doc: null,
    errors: [{
      type: "syntax",
      message: raw,
      line: lineMatch ? Number(lineMatch[1]) : null,
      column: colMatch ? Number(colMatch[1]) : null
    }]
  };
}

function checkTagStructure(xmlText){
  const errors = [];
  const stack = [];

  // Уберём комментарии (простая версия) чтобы regex по тегам не ловил мусор
  const cleaned = String(xmlText || "").replace(/<!--[\s\S]*?-->/g, "");

  const lines = cleaned.split("\n");
  // тег / закрывающий тег
  const tagRegex = /<\s*\/?\s*([A-Za-z_][A-Za-z0-9_.:-]*)\b[^>]*>/g;

  for (let i = 0; i < lines.length; i++){
    const lineText = lines[i];
    const lineNumber = i + 1;

    let match;
    while ((match = tagRegex.exec(lineText)) !== null){
      const full = match[0];

      // пропускаем декларации/инструкции
      if (full.startsWith("<?") || full.startsWith("<!")) continue;

      const tagName = match[1];

      const isClosing = /^<\s*\//.test(full);
      const isSelfClosing = /\/\s*>$/.test(full);

      if (isSelfClosing) continue;

      if (!isClosing){
        stack.push({ tag: tagName, line: lineNumber });
      } else {
        const last = stack.pop();
        if (!last){
          errors.push({
            type: "structure",
            message: `Лишний закрывающий тег </${tagName}>`,
            line: lineNumber,
            column: null
          });
        } else if (last.tag !== tagName){
          errors.push({
            type: "structure",
            message: `Несовпадение тегов: открыт <${last.tag}> (строка ${last.line}), закрыт </${tagName}>`,
            line: lineNumber,
            column: null
          });
        }
      }
    }
    tagRegex.lastIndex = 0;
  }

  for (const unclosed of stack){
    errors.push({
      type: "structure",
      message: `Тег <${unclosed.tag}> не закрыт`,
      line: unclosed.line,
      column: null
    });
  }

  return errors;
}

function validateXmlSyntaxAndStructure(xmlText){
  const parsed = parseXmlWithDetails(xmlText);
  const structureErrors = checkTagStructure(xmlText);

  const errors = [
    ...(parsed.errors || []),
    ...structureErrors
  ];

  return {
    ok: errors.length === 0 && parsed.ok,
    doc: parsed.ok ? parsed.doc : null,
    errors
  };
}

function renderXmlErrors(errors){
  if (!errors || errors.length === 0) return "✅ Синтаксис XML корректен. Ошибок структуры не найдено.";

  return errors.map((e, idx) => {
    const line = e.line ? `строка ${e.line}` : "строка: не определена";
    const col = e.column ? `, колонка ${e.column}` : "";
    return `${idx+1}) ❌ ${e.message}\n   → ${line}${col}`;
  }).join("\n\n");
}

/* ---------------------------------------------------------
   XML CHECK TAB wiring
--------------------------------------------------------- */
function initXmlCheckTab(){
  const input = $("xmlCheckFile");
  const btnCheck = $("btnXmlCheck");
  const btnFix = $("btnXmlFix");
  const report = $("xmlCheckReport");
  const status = $("xmlCheckStatus");

  if (!input || !btnCheck || !btnFix || !report || !status) return;

  btnCheck.addEventListener("click", async () => {
    status.textContent = "Проверка…";
    btnFix.disabled = true;
    report.textContent = "";
    lastXmlDoc = null;
    lastXmlIsParsable = false;

    const file = input.files?.[0];
    if (!file){
      status.textContent = "Ожидание";
      report.textContent = "Файл не выбран.";
      return;
    }
    lastXmlFileName = file.name || "data.xml";

    const text = await readFileAsText(file);

    // 1) Синтаксис/структура (well-formed + теги закрыты)
    const v = validateXmlSyntaxAndStructure(text);
    if (!v.ok){
      lastXmlIsParsable = false;
      status.textContent = "Ошибка синтаксиса/структуры";
      report.textContent =
        "Синтаксис XML некорректный или нарушена структура тегов.\n" +
        "Автоисправление недоступно (сначала нужно починить структуру файла).\n\n" +
        "Ошибки:\n" + renderXmlErrors(v.errors);
      return;
    }

    // 2) XML уже можно парсить и править
    lastXmlIsParsable = true;
    lastXmlDoc = v.doc;

    // 3) Минимальные обязательные
    const missing = checkMinimalMissing(lastXmlDoc);
    if (missing.length === 0){
      status.textContent = "ОК";
      report.textContent =
        "ОК: синтаксис корректен.\n" +
        "Минимально обязательные параметры присутствуют.\n\n" +
        "Можно нажать «Исправить и скачать», чтобы:\n" +
        "- заполнить пустые значения минимально обязательных параметров\n" +
        "- добавить подпись автора в конец файла";
      btnFix.disabled = false;
      return;
    }

    status.textContent = `Проблем: ${missing.length}`;
    report.textContent =
      "Синтаксис корректен.\n\n" +
      "Найдены проблемы (минимальный набор):\n" +
      missing.map(x => `- ${x.path}: ${x.reason}`).join("\n") +
      "\n\nНажмите «Исправить и скачать» — добавлю недостающие элементы/значения и подпись.";
    btnFix.disabled = false;
  });

  btnFix.addEventListener("click", () => {
    if (!lastXmlIsParsable || !lastXmlDoc){
      $("xmlCheckStatus").textContent = "Нужно проверить XML";
      $("xmlCheckReport").textContent = "Сначала нажмите «Проверить». Если синтаксис/структура битые — исправьте файл вручную.";
      return;
    }

    $("xmlCheckStatus").textContent = "Исправление…";

    const fixed = fixMinimal(lastXmlDoc);
    const xml = serializeXmlDoc(fixed);

    const base = lastXmlFileName.replace(/\.xml$/i, "");
    downloadText(base + "_fixed.xml", xml);

    $("xmlCheckStatus").textContent = "Скачано";
    $("xmlCheckReport").textContent += "\n\nСкачан файл: " + (base + "_fixed.xml");
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

if (!ifcAllowed()){
  $("ifcProtocolWarn").style.display = "block";
  $("tabIfc").classList.add("disabled");
}

updateFillProgress();
markInvalids("manual");
