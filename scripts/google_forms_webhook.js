/**
 * EVENT HQ BMSIT 2026 — Google Forms Automatic Team Registration
 * ===============================================================
 * 
 * Instructions:
 * 1. Open your Google Form (or linked Google Sheet).
 * 2. Click Extensions > Apps Script (or three-dots menu > Script editor).
 * 3. Replace the contents of Code.gs with this entire script.
 * 4. Replace <MY_PUBLIC_HTTPS_DOMAIN> below with your actual public HTTPS tunnel or domain.
 *    NOTE: Do NOT use localhost or 127.0.0.1. Google Apps Script runs in Google's cloud.
 * 5. Replace <PASTE_COPIED_SECRET_HERE> with your secret token copied from Event HQ Settings.
 * 6. Save the script (Ctrl+S).
 * 7. In the left navigation, click Triggers (alarm clock icon) > "+ Add Trigger".
 *    - Choose which function to run: onFormSubmit
 *    - Select event source: From form (or From spreadsheet)
 *    - Select event type: On form submit
 * 8. Click Save and authorize Google permissions when prompted.
 */

// Step 1: Active public HTTPS Cloudflare Tunnel endpoint:
const WEBHOOK_URL = "https://fees-roland-examining-holder.trycloudflare.com/api/v1/integrations/google-forms/webhook";

// Step 2: Copy your secret directly from Event HQ Settings > Google Forms Integration:
const WEBHOOK_SECRET = "<PASTE_COPIED_SECRET_HERE>";

function onFormSubmit(e) {
  try {
    let payload = {
      submission_id: "gform_" + Utilities.getUuid(),
      source: "google_forms"
    };

    if (e && e.response) {
      // Triggered directly from Google Form onFormSubmit
      payload.submission_id = "gform_" + e.response.getId();
      const itemResponses = e.response.getItemResponses();
      itemResponses.forEach(function(itemResponse) {
        const title = itemResponse.getItem().getTitle();
        const response = itemResponse.getResponse();
        payload[title] = response;
      });
    } else if (e && e.namedValues) {
      // Triggered from linked Google Sheet onFormSubmit
      for (const key in e.namedValues) {
        payload[key] = e.namedValues[key][0];
      }
    } else {
      Logger.log("Warning: Trigger event object is empty or manual execution. Cannot extract form responses.");
      return;
    }

    const options = {
      method: "post",
      contentType: "application/json",
      headers: {
        "X-Webhook-Secret": WEBHOOK_SECRET
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();
    const responseBody = response.getContentText();

    Logger.log("Event HQ Webhook Status: " + responseCode);
    Logger.log("Event HQ Webhook Response: " + responseBody);

    if (responseCode >= 200 && responseCode < 300) {
      Logger.log("Squad registration submitted successfully to Event HQ.");
    } else {
      Logger.log("Failed to submit to Event HQ. Status: " + responseCode + " - " + responseBody);
    }
  } catch (err) {
    Logger.log("Error posting to Event HQ Webhook: " + err.toString());
  }
}
