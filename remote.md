> ## Documentation Index
> Fetch the complete documentation index at: https://razorpay-881012b3.mintlify.site/llms.txt
> Use this file to discover all available pages before exploring further.

# Razorpay Remote MCP Server Setup

> Step-by-step guide to set up the Razorpay Remote MCP Server with zero infrastructure overhead.

<div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:"0.35rem 0.9rem",border:"1px solid rgba(128,128,128,0.28)",borderRadius:"0.5rem",padding:"0.45rem 0.75rem",margin:"0 0 1.25rem",fontSize:"0.875rem"}}>
  <span style={{fontWeight:600}}>Available in</span>
  <span>🇮🇳 India</span>
</div>

The Razorpay Remote MCP Server is a hosted solution that provides zero infrastructure overhead with automatic updates and high availability. This is the **recommended deployment option** for most users.

## Prerequisites

Before installing the Razorpay Remote MCP Server, ensure you have:

* **AI Assistant**: Claude Desktop, Cursor, Visual Studio Code, or similar AI-assisted application.
* **Razorpay Account**: Active Razorpay account with API access.
* **Authentication**: Generate [Razorpay API keys](/docs/payments/dashboard/account-settings/api-keys#generate-api-keys) from the Dashboard. Alternatively, you can use [OAuth](/docs/mcp-server/oauth).

## Step 1: Install Node.js

The Remote MCP Server requires Node.js and `npm`. Choose the installation method for your operating system:

### For Mac

<Tabs>
  <Tab title="Option 1: Download from Official Website (Recommended)">
    1. Go to [nodejs.org](http://nodejs.org/).
    2. Download the LTS (Long Term Support) version.
    3. Run the installer (.pkg file).
    4. Follow the installation prompts.
  </Tab>

  <Tab title="Option 2: Using Homebrew">
    Run the following command on terminal:

    ```bash Install Node.js theme={null}
    brew install node
    ```
  </Tab>
</Tabs>

### For Windows

<Tabs>
  <Tab title="Option 1: Download from Official Website (Recommended)">
    1. Go to [nodejs.org](http://nodejs.org/).
    2. Download the LTS version for Windows.
    3. Run the installer (.msi file).
    4. Follow the installation wizard.
    5. Make sure to check **Add to PATH** during installation.
  </Tab>

  <Tab title="Option 2: Using Chocolatey">
    Run the following command:

    ```bash Install Node.js theme={null}
    choco install nodejs
    ```
  </Tab>

  <Tab title="Option 3: Using Windows Package Manager">
    Run the following command:

    ```bash Install Node.js theme={null}
    winget install OpenJS.NodeJS
    ```
  </Tab>
</Tabs>

## Step 2: Verify Installation

After installing Node.js, open your terminal/command prompt and verify the installation:

```bash Verify Installation theme={null}
node --version
npm --version
npx --version
```

You should see version numbers for all three commands.

## Step 3: Authenticate Razorpay Account

Generate API keys and create a merchant token.

### Generate API Keys

Follow these steps to generate the API keys:

1. Log in to your [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. Navigate to **Account & Settings** → **API Keys**.
3. Generate your API keys (Key ID and Key Secret).
4. Copy both the Key ID and Key Secret.

### Encode Merchant Token

Encode your merchant token by running the following command in your terminal:

```bash Encode Merchant Token theme={null}
echo <RAZORPAY_API_KEY>:<RAZORPAY_API_SECRET> | base64
# Output: cnpwX3Rlc3RfYWJjMTIzOnNlY3JldF9kZWY0NTY=
```

<Warning>
  **Watch Out!**

  Replace `<RAZORPAY_API_KEY>` and `<RAZORPAY_API_SECRET>` with your actual credentials.
</Warning>

Save this base64-encoded token as you will need it for configuration.

## Step 4: Configure Your AI-assisted Application

Choose your AI-assisted application and follow the corresponding platform setup guide.

<Warning>
  **Deprecation Notice**

  Effective **August 13, 2025**, the endpoint `https://mcp.razorpay.com/sse` is deprecated and replaced by `https://mcp.razorpay.com/mcp`, which supports streamable HTTP responses for improved performance. Update your integrations immediately to avoid service disruptions. Refer to the [changelog](/docs/api/changelog).
</Warning>

<CardGroup cols={2}>
  <Card title="Claude" href="/docs/mcp-server/integrations/claude">
    Connect using the official Razorpay connector or Claude Code (CLI).
  </Card>

  <Card title="ChatGPT" href="/docs/mcp-server/integrations/chatgpt">
    Install the official Razorpay app and authorise it using OAuth.
  </Card>

  <Card title="Cursor" href="/docs/mcp-server/integrations/cursor">
    Add the server through the mcp-remote bridge in mcp.json.
  </Card>

  <Card title="Visual Studio Code" href="/docs/mcp-server/integrations/vs-code">
    Configure agent mode with a secure merchant token prompt.
  </Card>

  <Card title="Windsurf" href="/docs/mcp-server/integrations/windsurf">
    Add the server to the Cascade agent via mcp\_config.json.
  </Card>

  <Card title="Replit" href="/docs/mcp-server/integrations/replit">
    Add the server from Integrations settings and authorise via OAuth.
  </Card>

  <Card title="Gemini CLI" href="/docs/mcp-server/integrations/gemini-cli">
    Add the server to the mcpServers block in settings.json.
  </Card>
</CardGroup>

## Step 5: Restart Application

Restart your AI assistant application after adding the configuration. You should see Razorpay MCP tools become available. Test the connection by asking: **Show me available Razorpay tools**.

If successful, you should see a list of available Razorpay MCP tools.

## Next Steps

Once your Remote MCP Server is set up:

1. **Explore Use Cases**: Review [practical examples](/docs/mcp-server/use-cases) of AI-powered payment operations.
2. **Learn Available Tools**: Check the [Tools Reference](/docs/mcp-server/tools-reference) for complete capabilities.
3. **Advanced Configuration**: See [Configuration Guide](/docs/mcp-server/configuration) for additional options.
4. **Start Building**: Begin using natural language commands to interact with Razorpay APIs
