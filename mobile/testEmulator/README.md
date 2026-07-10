# AIRA Android Emulator Testing Guide

This guide explains how to set up **Android Studio**, run the **Android Emulator**, and test the mobile application using either your **deployed Railway backend** or a **local backend**.

---

## Testing Options

You can test the mobile application using one of two configurations:

* **Option A (Recommended & Easiest): Deployed Railway Backend**
  * Uses your live backend hosted on Railway.
  * No need to run PostgreSQL or Python on your laptop.
  * Ideal if your Railway backend is already configured with Gemini, Sarvam, and Cartesia API keys.
* **Option B: Local Backend**
  * Runs everything on your laptop.
  * Requires Docker (for PostgreSQL) and Python.

---

## Option A: Testing with Deployed Railway Backend

Since your backend is already deployed to Railway, testing is extremely simple:

### Step 1: Open the Project in Android Studio
1. Open **Android Studio** on your computer.
2. Select **File > Open** (or **Open an Existing Project** from the Welcome screen).
3. Browse and select the directory:
   `c:\Projects\AIRA\Aira\mobile\android`
4. Wait for Android Studio to import the project and sync Gradle.

### Step 2: Create and Start the Android Emulator
If you do not have an active emulator configured in Android Studio:
1. Open the **Device Manager** (located in the top-right toolbars or under **Tools > Device Manager**).
2. Click **Create Device** (or the **+** icon).
3. Select a phone profile (e.g., **Pixel 8**) and click **Next**.
4. Choose **API Level 34** (UpsideDownCake) under the "Recommended" tab. Download it if necessary, then click **Next**.
5. Name the device and click **Finish**.
6. Click the **Play (Launch)** button next to your emulator to start it.

### Step 3: Run the App on the Emulator
1. Click the green **Run (Play)** button in Android Studio's top toolbar to build and deploy the app onto the active emulator.
2. Once the app launches on the emulator, you will see the **AIRA Home Screen**.

### Step 4: Configure the App with your Railway URL
1. In the top-right corner of the Home Screen, tap the **Settings** gear icon.
2. Navigate to the **Connection Status** screen.
3. In the **Server WebSocket URL** input field, enter your Railway WebSocket URL:
   ```
   wss://your-railway-app.up.railway.app/ws
   ```
   *(Replace `your-railway-app.up.railway.app` with your actual Railway app URL. Ensure it starts with `wss://` and ends with `/ws`)*.
4. Tap **Test Connection**.
   * The status circle should turn green and show **"Connected successfully!"** with latency stats.
5. Tap the back button in the top-left corner to return to the Home Screen.

### Step 5: Test Voice Call
1. Tap the **Settings** gear and go to the **Permissions** screen. Grant both **Record Audio (Microphone)** and **Phone Call Permissions**.
2. Go back to the Home Screen and toggle the **AI Call Handler Status** switch to **ON** (the central bubble will turn green and say **ACTIVE**).
3. Click the blue **Simulate Incoming Call (Audio Echo)** button at the bottom of the screen.
4. Speak into your laptop's mic. The audio is streamed directly to Railway, processed by Gemini, Sarvam, and Cartesia, and the AI agent's voice response will play back through your speakers!

---

## Option B: Testing with a Local Backend

If you ever need to debug code changes locally before pushing to Railway, follow these steps:

### Step 1: Run the Local Database
1. Open a terminal in `c:\Projects\AIRA\Aira\backend`.
2. Run:
   ```bash
   docker-compose up -d postgres
   ```
   *(Starts PostgreSQL on host port `5435`)*.

### Step 2: Configure & Start the Python Backend
1. Open a terminal in `c:\Projects\AIRA\Aira\mobile\backend`.
2. Set up virtual environment and install packages:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set your API keys. Make sure your database URL points to port `5435`:
   ```env
   DATABASE_URL_AIRA=postgresql://recep:recep@localhost:5435/recep
   ```
4. Verify packages with `python check_backend.py`.
5. Run the server:
   ```bash
   python main.py
   ```
   *(Starts server on port `8000`)*.

### Step 3: Run the App and Connect via `10.0.2.2`
1. Open `mobile/android` in Android Studio and run the app on the emulator.
2. Go to **Settings > Connection Status**.
3. Set the URL to the special Android host redirect address:
   ```
   ws://10.0.2.2:8000/ws
   ```
4. Tap **Test Connection** to verify, then go back to the Home Screen, activate the agent, and simulate the call.
