const CLOUD_RUN_URL =
  "https://merchant-onboarding-triage-243535079045.asia-south2.run.app/triage";

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Merchant Triage")
    .addItem("Run Triage", "runTriage")
    .addToUi();
}

function runTriage() {
  const ui = SpreadsheetApp.getUi();

  try {
    const response = UrlFetchApp.fetch(CLOUD_RUN_URL, {
      method: "post",
      muteHttpExceptions: true,
      contentType: "application/json"
    });

    const statusCode = response.getResponseCode();
    const responseText = response.getContentText();

    if (statusCode >= 200 && statusCode < 300) {
      ui.alert(
        "Triage Complete",
        responseText.substring(0, 1000),
        ui.ButtonSet.OK
      );
    } else {
      ui.alert(
        "Triage Failed",
        "HTTP " + statusCode + "\n\n" +
        responseText.substring(0, 1500),
        ui.ButtonSet.OK
      );
    }
  } catch (error) {
    ui.alert(
      "Triage Error",
      error.toString(),
      ui.ButtonSet.OK
    );
  }
}
