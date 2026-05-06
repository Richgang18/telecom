# 🖱️ Desktop Shortcut Setup

## Quick Setup (Easiest)

**Just double-click this file:**
```
SETUP_SHORTCUT.bat
```

That's it! A shortcut will appear on your desktop.

---

## What It Does

1. Creates an application icon (phone icon)
2. Creates a desktop shortcut named "Smart Outbound Dialer"
3. Configures the shortcut to launch the app with one click

---

## After Setup

You'll see this on your desktop:

```
🖥️ Desktop
   📞 Smart Outbound Dialer  ← Double-click this!
```

**Double-click the shortcut** to launch the application.

---

## Manual Setup (If Automatic Fails)

### Option 1: Using VBScript (Most Compatible)

1. Double-click: `create_shortcut.vbs`
2. Click OK on the success message
3. Done!

### Option 2: Using PowerShell

1. Right-click `create_shortcut.ps1`
2. Select "Run with PowerShell"
3. If prompted, allow execution
4. Done!

### Option 3: Manual Shortcut Creation

1. Right-click on your desktop
2. Select **New → Shortcut**
3. For location, enter:
   ```
   python.exe "D:\telecom\voip\smart_routing\desktop_app.py"
   ```
   (Adjust path if different)
4. Click **Next**
5. Name it: `Smart Outbound Dialer`
6. Click **Finish**
7. Right-click the shortcut → **Properties**
8. Set **Start in:** to: `D:\telecom\voip\smart_routing`
9. Click **Change Icon** → **Browse**
10. Select: `D:\telecom\voip\smart_routing\app_icon.ico`
11. Click **OK** → **OK**

---

## Troubleshooting

### Shortcut Created But Won't Launch

**Problem:** Double-clicking does nothing or shows error

**Solution:**
1. Right-click shortcut → Properties
2. Verify **Target** shows correct Python path
3. Verify **Start in** shows correct folder
4. Try changing Target to:
   ```
   C:\Windows\py.exe "D:\telecom\voip\smart_routing\desktop_app.py"
   ```

### Icon Not Showing

**Problem:** Shortcut has default Python icon

**Solution:**
1. Run `python create_icon.py` manually
2. Verify `app_icon.ico` was created
3. Right-click shortcut → Properties → Change Icon
4. Browse to `app_icon.ico`

### "Python Not Found" Error

**Problem:** Shortcut says Python is not recognized

**Solution:**
1. Find your Python installation:
   ```
   where python
   ```
2. Edit shortcut Target to use full path:
   ```
   "C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe" "D:\telecom\voip\smart_routing\desktop_app.py"
   ```

---

## Files Created

After running setup:

- ✅ `app_icon.ico` - Application icon (phone symbol)
- ✅ Desktop shortcut - "Smart Outbound Dialer"

---

## Customizing the Icon

Want a different icon?

1. Find or create a `.ico` file
2. Name it `app_icon.ico`
3. Replace the existing file
4. Right-click shortcut → Properties → Change Icon
5. Browse to new icon

---

## Removing the Shortcut

Simply:
1. Right-click the desktop shortcut
2. Select **Delete**

The application files remain untouched.

---

## Alternative: Pin to Taskbar

After creating the shortcut:

1. Double-click to launch the app
2. Right-click the app icon in taskbar
3. Select **Pin to taskbar**
4. Now you can launch from taskbar!

---

## Alternative: Start Menu

To add to Start Menu:

1. Press `Win + R`
2. Type: `shell:programs`
3. Press Enter
4. Copy the desktop shortcut here
5. Now searchable from Start Menu!

---

**Setup complete! Enjoy your one-click launcher! 🚀**
