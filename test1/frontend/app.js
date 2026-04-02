const submitBtn = document.getElementById("submitBtn");
const statusEl = document.getElementById("status");
const logsEl = document.getElementById("logs");
const summaryEl = document.getElementById("summary");
const apiBaseInput = document.getElementById("apiBase");

function getDefaultApiBase() {
  const protocol = window.location.protocol === "https:" ? "https:" : "http:";
  const host = window.location.hostname || "127.0.0.1";
  return `${protocol}//${host}:5051`;
}

apiBaseInput.value = getDefaultApiBase();

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}

function renderLogs(logs) {
  logsEl.innerHTML = "";
  if (!logs || logs.length === 0) {
    logsEl.textContent = "暂无日志";
    return;
  }
  const ul = document.createElement("ul");
  logs.forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    ul.appendChild(li);
  });
  logsEl.appendChild(ul);
}

function renderSummary(summary) {
  summaryEl.innerHTML = "";
  if (!summary || Object.keys(summary).length === 0) {
    summaryEl.textContent = "暂无摘要";
    return;
  }
  const ul = document.createElement("ul");
  Object.entries(summary).forEach(([k, v]) => {
    const li = document.createElement("li");
    li.textContent = `${k}: ${v}`;
    ul.appendChild(li);
  });
  summaryEl.appendChild(ul);
}

submitBtn.addEventListener("click", async () => {
  const apiBase = document.getElementById("apiBase").value.trim();
  const standard = document.getElementById("standard").files[0];
  const manual = document.getElementById("manual").files[0];

  if (!apiBase) {
    setStatus("请填写后端地址。", true);
    return;
  }
  if (!standard || !manual) {
    setStatus("请同时选择两个 Excel 文件。", true);
    return;
  }

  setStatus("正在上传并核对，请稍候...");
  renderLogs([]);
  renderSummary({});

  const formData = new FormData();
  formData.append("standard", standard);
  formData.append("manual", manual);

  try {
    const resp = await fetch(`${apiBase}/api/compare`, {
      method: "POST",
      body: formData,
    });
    const data = await resp.json();
    if (!resp.ok) {
      setStatus(data.error || "核对失败", true);
      return;
    }

    renderLogs(data.logs);
    renderSummary(data.summary);
    const downloadUrl = `${apiBase}${data.download_url}`;
    setStatus(`核对完成，点击下载结果：${downloadUrl}`);

    const link = document.createElement("a");
    link.href = downloadUrl;
    link.textContent = "下载核对结果 Excel";
    link.target = "_blank";
    link.className = "download";
    statusEl.innerHTML = "";
    statusEl.appendChild(link);
  } catch (err) {
    setStatus(`请求失败: ${err}`, true);
  }
});
