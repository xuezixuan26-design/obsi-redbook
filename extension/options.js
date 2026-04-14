const vaultNameInput = document.getElementById("vaultName");
const folderPathInput = document.getElementById("folderPath");
const saveBtn = document.getElementById("saveBtn");
const status = document.getElementById("status");

async function loadOptions() {
  const stored = await chrome.storage.sync.get({
    vaultName: "",
    folderPath: "Inbox/Xiaohongshu"
  });
  vaultNameInput.value = stored.vaultName;
  folderPathInput.value = stored.folderPath;
}

async function saveOptions() {
  await chrome.storage.sync.set({
    vaultName: vaultNameInput.value.trim(),
    folderPath: folderPathInput.value.trim()
  });
  status.textContent = "Saved.";
}

saveBtn.addEventListener("click", saveOptions);
loadOptions();
