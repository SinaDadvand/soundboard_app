# Discord Bot Setup Guide for Virtual Soundboard

This guide walks you through creating a free Discord Bot that can join your Discord voice channels and stream soundboard clips with real-time DSP effects (Pitch, Speed, Echo, Reverb).

---

## Step 1: Create a Discord Application
1. Go to the **[Discord Developer Portal](https://discord.com/developers/applications)** and log in with your Discord account.
2. Click **New Application** (top right).
3. Enter a name (e.g., `Virtual Soundboard`) and click **Create**.

---

## Step 2: Configure the Bot & Copy Token
1. In the left navigation menu, click **Bot**.
2. Click **Reset Token** (or **Copy Token**) to reveal your Bot Token.
   > [!CAUTION]
   > Keep this token private! Anyone with your token can control the bot.
3. Scroll down to **Privileged Gateway Intents**:
   * Enable **Message Content Intent** (Toggle ON).
   * Enable **Server Members Intent** (Optional, Toggle ON).
4. Click **Save Changes**.

---

## Step 3: Generate Invite Link with Voice Permissions
1. In the left menu, click **OAuth2** ➔ **URL Generator**.
2. Under **Scopes**, check:
   * ✅ `bot`
   * ✅ `applications.commands`
3. Under **Bot Permissions**, check:
   * ✅ `Connect` (Voice)
   * ✅ `Speak` (Voice)
   * ✅ `Use Voice Activity` (Voice)
   * ✅ `Send Messages` (Text)
   * ✅ `Read Message History` (Text)
4. Copy the **Generated URL** at the bottom of the page.
5. Paste this URL into your browser, select your Discord server, and click **Authorize**.

---

## Step 4: Connecting the Bot to your Soundboard
You can connect the bot using either:

### Option A: From the Soundboard Web Dashboard
1. Open the Soundboard web page (locally or on Cloud Run).
2. Click **⚙️ Settings** (top right).
3. Under **3. Discord Voice Bot**:
   * Paste your **Bot Token** and click **Connect**.
   * Select your voice channel from the dropdown and click **Join Voice**.

### Option B: Via Environment Variables (Recommended for Cloud Run)
Set the following environment variables:
* `DISCORD_BOT_TOKEN`: `your_bot_token_here`
* `DISCORD_VOICE_CHANNEL_ID`: `your_voice_channel_id_here` (optional, for auto-joining)

---

## Step 5: Discord Chat Commands
Once the bot is in your server, you can also control it directly from Discord text channels:
* `!join` — Bot joins your current voice channel.
* `!leave` — Bot leaves the voice channel.
* `!sounds` — Lists available soundboard clips.
