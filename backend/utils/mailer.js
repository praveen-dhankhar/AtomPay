const SibApiV3Sdk = require("sib-api-v3-sdk");

const defaultClient = SibApiV3Sdk.ApiClient.instance;
defaultClient.authentications['api-key'].apiKey = process.env.BREVO_API_KEY;

const sendOTPEmail = async (email, otp) => {
  const apiInstance = new SibApiV3Sdk.TransactionalEmailsApi();
  await apiInstance.sendTransacEmail({
    sender: { email: "akshay.dhankhar.ji@gmail.com", name: "AtomPay" },
    to: [{ email }],
    subject: "Your AtomPay OTP ⚡",
    htmlContent: `
      <div style="font-family:sans-serif;max-width:400px;margin:auto">
        <h2 style="color:#FF5722">⚡ AtomPay</h2>
        <p>Your Login OTP:</p>
        <h1 style="color:#FF5722;letter-spacing:8px">${otp}</h1>
        <p>Expires in 2 minutes.</p>
      </div>
    `
  });
};

module.exports = sendOTPEmail;
