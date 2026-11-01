# 💸 Smart Expense & Budget Tracker

A responsive web application with **dynamic per-spend budgeting, automatic overshoot re-balancing, 1-tap quick add buttons, piggy bank savings rollover, and visual burn rate analytics**. Designed for desktop and mobile browsers.

---

## 🌟 Key Features

1. **Custom Categories with Per-Spend Frequency Rules**:
   - Define targets like **₹250 per spend** with a frequency of **8 times a month** (Total monthly budget = ₹2,000).
   - Easily add, update, and manage categories (Food, Fuel, Movies, Groceries, etc.).

2. **Real-Time Dynamic Overshoot Warning & Re-balancing**:
   - If you overshoot your per-spend target (e.g., ₹280 instead of ₹250):
     - Displays an instant overshoot alert.
     - Automatically recalculates your allowed average for remaining spends:
       $$\text{New Recommended Avg} = \frac{\text{Remaining Budget}}{\text{Remaining Planned Spends}}$$

3. **🐷 Savings Piggy Bank (Monthly Rollover)**:
   - Underspent budget from previous months automatically rolls over into the current month's budget pool.
   - Can be toggled on/off in the sidebar anytime.

4. **⚡ 1-Tap Quick Add Buttons (Mobile First)**:
   - Tap preset shortcuts right from your phone (e.g., `☕ Chai & Snack (₹50)`, `🍱 Daily Thali (₹150)`, `🍔 Standard Food (₹250)`).
   - Add/delete custom quick buttons in the settings tab.

5. **📈 Visual Trends & Ideal Burn Rate Charts**:
   - **Cumulative Spend vs. Ideal Linear Burn Line**: Easily see if you are burning through your budget faster than the days of the month progress.
   - **Category Comparison Bar Chart**: Side-by-side comparison of budget vs. actual spend for each category.

6. **History & CSV Export**:
   - Monthly transaction logs with overshoot status markers.
   - 1-click CSV download for offline archiving.

---

## 🚀 How to Run

### Run on your PC:
```bash
python -m streamlit run main.py
```

### Access on your Phone (Free & Local Wi-Fi):
1. Once running, copy the **Network URL** displayed in your terminal (e.g. `http://192.168.x.x:8501`).
2. Open it in Chrome or Safari on your phone.
3. Tap **"Add to Home Screen"** to use it like a standalone app.

### Deploy to the Cloud (Free Forever):
1. Push this folder to a GitHub repository.
2. Sign in to **[share.streamlit.io](https://share.streamlit.io)** with GitHub.
3. Select your repository and `main.py` -> click **Deploy**.
