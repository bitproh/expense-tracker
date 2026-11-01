import streamlit as st
import datetime
import calendar
import pandas as pd
import altair as alt
import db

st.set_page_config(
    page_title="SpendWise - Smart Budget & Expense Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Polished Modern Dark/Light Adaptive CSS Styling
st.markdown("""
<style>
    /* Global modern typography & spacing */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    
    /* Header card */
    .app-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: white;
        padding: 22px 26px;
        border-radius: 16px;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.1);
    }
    .app-header h1 {
        margin: 0;
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #f8fafc;
    }
    .app-header p {
        margin: 4px 0 0 0;
        color: #94a3b8;
        font-size: 0.95rem;
    }

    /* Metric Cards */
    .stat-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        margin-bottom: 12px;
    }
    
    /* Alert Banners */
    .warning-box {
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-left: 5px solid #f59e0b;
        color: #92400e;
        padding: 14px 16px;
        border-radius: 10px;
        margin: 12px 0;
    }
    .success-box {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 5px solid #22c55e;
        color: #166534;
        padding: 14px 16px;
        border-radius: 10px;
        margin: 12px 0;
    }
    .danger-box {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 5px solid #ef4444;
        color: #991b1b;
        padding: 14px 16px;
        border-radius: 10px;
        margin: 12px 0;
    }
    .piggy-box {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #86efac;
        color: #14532d;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 16px;
        font-size: 0.95rem;
    }

    /* Badges */
    .badge-pill-over {
        background: #fee2e2;
        color: #b91c1c;
        padding: 3px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
    }
    .badge-pill-under {
        background: #dcfce7;
        color: #15803d;
        padding: 3px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
    }
    
    /* Quick log row item */
    .recent-row {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
db.init_db()

# Sidebar: Controls & Period Selection
st.sidebar.markdown("### 🗓️ View Period")
today = datetime.date.today()
current_year = today.year
current_month = today.month

year_choice = st.sidebar.selectbox("Select Year", options=[current_year - 1, current_year, current_year + 1], index=1)
month_names = list(calendar.month_name)[1:]
month_choice_name = st.sidebar.selectbox("Select Month", options=month_names, index=current_month - 1)
selected_month = month_names.index(month_choice_name) + 1

# Piggy Bank Savings Rollover Toggle
st.sidebar.divider()
st.sidebar.markdown("### 🐷 Savings Piggy Bank")
enable_rollover = st.sidebar.checkbox(
    "Enable Rollover Savings",
    value=True,
    help="When enabled, any underspent budget from the previous month is carried over into this month's budget pool."
)

total_prev_savings, cat_prev_savings = db.get_rollover_from_previous_month(year_choice, selected_month)
if enable_rollover and total_prev_savings > 0:
    st.sidebar.success(f"🎉 **+₹{total_prev_savings:,.2f}** savings rolled over from last month!")

# Sidebar Category Creation
st.sidebar.divider()
st.sidebar.markdown("### ⚙️ Categories")
categories = db.get_categories()

with st.sidebar.expander("➕ Create New Category"):
    with st.form("new_category_form", clear_on_submit=True):
        new_cat_name = st.text_input("Name (e.g. Food, Fuel, Shopping)")
        new_cat_icon = st.text_input("Emoji Icon", value="🏷️")
        new_cat_limit = st.number_input("Limit Per Spend (₹)", min_value=1.0, value=250.0, step=10.0)
        new_cat_freq = st.number_input("Monthly Frequency (Times)", min_value=1, value=8, step=1)
        submitted = st.form_submit_button("Create Category", width="stretch")
        if submitted:
            if new_cat_name.strip():
                ok, msg = db.add_category(new_cat_name, new_cat_limit, new_cat_freq, new_cat_icon)
                if ok:
                    st.toast(msg, icon="✅")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Category name cannot be empty.")

# App Header Banner
st.markdown(f"""
<div class="app-header">
    <h1>💳 SpendWise</h1>
    <p>Target Budgeting & Dynamic Limit Balancing • Active Period: <strong>{month_choice_name} {year_choice}</strong></p>
</div>
""", unsafe_allow_html=True)

# Navigation Tabs
tab_add, tab_overview, tab_charts, tab_categories, tab_history, tab_reset = st.tabs([
    "➕ Log Expense", 
    "📊 Monthly Overview", 
    "📈 Visual Trends", 
    "🎯 Categories & Shortcuts", 
    "📜 History & Delete",
    "🔄 Reset Provisions"
])

# ----------------- TAB 1: LOG EXPENSE -----------------
with tab_add:
    # 1-Tap Quick Action Buttons on Mobile
    templates = db.get_quick_templates()
    if templates:
        st.markdown("#### ⚡ 1-Tap Quick Add (Phone Friendly)")
        st.caption("One tap to log instant expenses for today:")
        t_cols = st.columns(min(len(templates), 4))
        for i, t in enumerate(templates):
            col_target = t_cols[i % len(t_cols)]
            with col_target:
                btn_label = f"{t['icon']} {t['label']} (₹{t['amount']:.0f})"
                if st.button(btn_label, key=f"quick_{t['id']}", width="stretch"):
                    new_id = db.add_expense(t["category_id"], t["amount"], today, f"Quick add: {t['label']}")
                    st.session_state["just_logged_id"] = new_id
                    st.toast(f"✅ Logged ₹{t['amount']:.0f} for {t['category_name']}!", icon="⚡")
                    st.rerun()
        st.divider()

    st.markdown("#### 📝 Manual Expense Entry")
    if not categories:
        st.warning("Please add at least one category in the sidebar to start logging.")
    else:
        cat_map = {f"{c['icon']} {c['name']} (Target: ₹{c['limit_per_time']:.0f} × {c['frequency_per_month']}x/mo)": c for c in categories}
        selected_cat_str = st.selectbox("Select Category", list(cat_map.keys()))
        selected_cat = cat_map[selected_cat_str]

        rolled_over_for_cat = cat_prev_savings.get(selected_cat["id"], 0.0) if enable_rollover else 0.0
        stats = db.get_category_monthly_stats(selected_cat["id"], year_choice, selected_month, rolled_over_for_cat)

        col1, col2 = st.columns([1, 1])
        with col1:
            amount_input = st.number_input("Amount Spent (₹)", min_value=1.0, value=float(selected_cat["limit_per_time"]), step=10.0)
            expense_date = st.date_input("Expense Date", value=today)
        with col2:
            note_input = st.text_input("Note / Tag (Optional)", placeholder="e.g. Swiggy lunch, petrol, groceries")
            st.write("") 
            submit_expense = st.button("💾 Save Expense", type="primary", width="stretch")

        # Dynamic warning logic
        limit = selected_cat["limit_per_time"]
        diff = amount_input - limit

        if diff > 0:
            st.markdown(f"""
            <div class="warning-box">
                ⚠️ <strong>Overshoot Alert:</strong> Spending <strong>₹{amount_input:.2f}</strong> exceeds your per-spend target of <strong>₹{limit:.2f}</strong> by <strong>₹{diff:.2f}</strong>.
            </div>
            """, unsafe_allow_html=True)
            
            projected_total = stats["total_spent"] + amount_input
            projected_rem_budget = stats["effective_budget"] - projected_total
            projected_spends_left = max(0, selected_cat["frequency_per_month"] - (stats["spends_done"] + 1))
            
            if projected_spends_left > 0:
                projected_next_avg = max(0.0, projected_rem_budget / projected_spends_left)
                st.info(f"💡 **Dynamic Adjustment:** To stay strictly within your ₹{stats['effective_budget']:.2f} monthly budget, your average limit for the remaining **{projected_spends_left}** spends adjusts to **₹{projected_next_avg:.2f}** per spend.")
            else:
                if projected_rem_budget < 0:
                    st.error(f"🚨 This spend will cause you to exceed your total monthly budget by ₹{abs(projected_rem_budget):.2f}!")
                else:
                    st.warning("⚠️ This will be your last planned spend for this category this month.")
        else:
            st.markdown(f"""
            <div class="success-box">
                ✅ <strong>Within Target:</strong> ₹{amount_input:.2f} is within your target limit of ₹{limit:.2f}.
            </div>
            """, unsafe_allow_html=True)

        if submit_expense:
            new_id = db.add_expense(selected_cat["id"], amount_input, expense_date, note_input)
            st.session_state["just_logged_id"] = new_id
            st.toast(f"Added ₹{amount_input:.2f} for {selected_cat['name']}!", icon="✅")
            st.rerun()

    # Provision to Delete an Expense Immediately After Logging
    st.divider()
    st.markdown("#### 🕒 Just Logged Expenses (1-Click Undo / Delete)")
    st.caption("Mistyped an amount? Delete or undo any recent entry right here:")
    
    recent_entries = db.get_recent_expenses(limit=4)
    if not recent_entries:
        st.info("No expenses logged yet.")
    else:
        for item in recent_entries:
            c_info, c_action = st.columns([4, 1.2])
            with c_info:
                note_snippet = f" • <i>{item['note']}</i>" if item['note'] else ""
                st.markdown(f"""
                <div class="recent-row">
                    <div>
                        <strong>{item['icon']} {item['category_name']}</strong> — <span style="font-weight:700; color:#0f172a;">₹{item['amount']:,.2f}</span>
                        <br><span style="font-size:0.8rem; color:#64748b;">📅 {item['date']}{note_snippet}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_action:
                st.write("")
                if st.button("🗑️ Delete", key=f"quick_del_{item['id']}", width="stretch"):
                    db.delete_expense(item["id"])
                    st.toast(f"Deleted #{item['id']} (₹{item['amount']:.2f})", icon="🗑️")
                    st.rerun()

# ----------------- TAB 2: MONTHLY OVERVIEW -----------------
with tab_overview:
    all_expenses = db.get_monthly_expenses(year_choice, selected_month)
    total_spent = sum(e["amount"] for e in all_expenses)
    base_budget = sum(c["monthly_budget"] for c in categories)
    rolled_budget = total_prev_savings if enable_rollover else 0.0
    effective_total_budget = base_budget + rolled_budget
    total_spends_count = len(all_expenses)
    
    overall_avg_per_spend = (total_spent / total_spends_count) if total_spends_count > 0 else 0.0
    budget_remaining = effective_total_budget - total_spent
    is_overspending = total_spent > effective_total_budget

    if enable_rollover and rolled_budget > 0:
        st.markdown(f"""
        <div class="piggy-box">
            🐷 <strong>Savings Piggy Bank Active:</strong> ₹{rolled_budget:,.2f} unspent from previous month was rolled into this month's budget! Total pool: <strong>₹{effective_total_budget:,.2f}</strong>.
        </div>
        """, unsafe_allow_html=True)

    # Clean Top Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "Total Spent",
            f"₹{total_spent:,.2f}",
            delta=f"{'-' if is_overspending else '+'}₹{abs(budget_remaining):,.2f} rem",
            delta_color="inverse" if is_overspending else "normal"
        )
    with m2:
        st.metric("Total Monthly Budget", f"₹{effective_total_budget:,.2f}")
    with m3:
        st.metric("Avg Spent per Transaction", f"₹{overall_avg_per_spend:,.2f}")
    with m4:
        status_text = "OVERSPENDING 🚨" if is_overspending else "UNDER BUDGET 🟢"
        st.metric("Budget Status", status_text)

    st.divider()

    # Category Breakdown Cards
    st.subheader("Category Breakdown & Dynamic Limits")
    
    if not categories:
        st.info("No categories defined yet.")
    else:
        for cat in categories:
            cat_rollover = cat_prev_savings.get(cat["id"], 0.0) if enable_rollover else 0.0
            stats = db.get_category_monthly_stats(cat["id"], year_choice, selected_month, cat_rollover)
            if not stats:
                continue

            with st.container():
                c1, c2, c3, c4 = st.columns([2.5, 2, 2, 2.5])
                with c1:
                    st.markdown(f"### {cat['icon']} {cat['name']}")
                    st.caption(f"Rule: Up to ₹{cat['limit_per_time']:.0f} × {cat['frequency_per_month']} times/month")
                    if cat_rollover > 0:
                        st.caption(f"🐷 Rolled over: +₹{cat_rollover:,.2f}")

                with c2:
                    st.write("**Spent vs Budget**")
                    st.write(f"₹{stats['total_spent']:,.2f} / ₹{stats['effective_budget']:,.2f}")
                    pct = min(1.0, stats['total_spent'] / stats['effective_budget']) if stats['effective_budget'] > 0 else 0
                    st.progress(pct)

                with c3:
                    st.write("**Frequency Track**")
                    st.write(f"**{stats['spends_done']}** of **{cat['frequency_per_month']}** spends done")
                    st.caption(f"{stats['spends_left']} spends remaining")

                with c4:
                    st.write("**Dynamic Next Spend Avg**")
                    if stats['spends_left'] > 0:
                        st.markdown(f"**₹{stats['recommended_next_avg']:.2f}** / spend")
                        if stats['recommended_next_avg'] < cat['limit_per_time']:
                            diff_down = cat['limit_per_time'] - stats['recommended_next_avg']
                            st.caption(f":red[↓ ₹{diff_down:.2f} less due to past overshoot]")
                        else:
                            st.caption(":green[✓ On track / extra buffer available]")
                    else:
                        if stats['remaining_budget'] < 0:
                            st.markdown(f"<span class='badge-pill-over'>Over budget by ₹{abs(stats['remaining_budget']):.2f}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("<span class='badge-pill-under'>All planned spends done</span>", unsafe_allow_html=True)

                st.divider()

# ----------------- TAB 3: VISUAL TRENDS -----------------
with tab_charts:
    st.subheader(f"📊 Expense Trends & Budget Burn Rate ({month_choice_name} {year_choice})")
    expenses = db.get_monthly_expenses(year_choice, selected_month)

    if not expenses:
        st.info("No expense data available for this month yet to plot charts.")
    else:
        days_in_month = calendar.monthrange(year_choice, selected_month)[1]
        
        df_exp = pd.DataFrame(expenses)
        df_exp["day"] = pd.to_datetime(df_exp["date"]).dt.day
        daily_sum = df_exp.groupby("day")["amount"].sum().reset_index()

        all_days = pd.DataFrame({"day": list(range(1, days_in_month + 1))})
        merged_days = pd.merge(all_days, daily_sum, on="day", how="left").fillna(0)
        merged_days["Cumulative Spent"] = merged_days["amount"].cumsum()

        eff_budget = effective_total_budget if effective_total_budget > 0 else 1000
        merged_days["Ideal Linear Burn"] = (merged_days["day"] / days_in_month) * eff_budget

        chart_df = pd.melt(
            merged_days,
            id_vars=["day"],
            value_vars=["Cumulative Spent", "Ideal Linear Burn"],
            var_name="Metric",
            value_name="Amount (₹)"
        )

        burn_chart = alt.Chart(chart_df).mark_line(point=True).encode(
            x=alt.X("day:Q", title="Day of the Month", scale=alt.Scale(domain=[1, days_in_month])),
            y=alt.Y("Amount (₹):Q", title="Rupees (₹)"),
            color=alt.Color("Metric:N", scale=alt.Scale(
                domain=["Cumulative Spent", "Ideal Linear Burn"],
                range=["#ef4444" if is_overspending else "#0284c7", "#94a3b8"]
            )),
            strokeDash=alt.condition(
                alt.datum.Metric == "Ideal Linear Burn",
                alt.value([5, 5]),
                alt.value([0])
            ),
            tooltip=["day:Q", "Metric:N", "Amount (₹):Q"]
        ).properties(
            title="Actual Spending Trajectory vs. Ideal Budget Burn Rate",
            height=340
        ).interactive()

        st.altair_chart(burn_chart, width="stretch")
        st.caption("ℹ️ If the **Cumulative Spent** line rises above the dashed line, you are spending faster than the month progresses.")

        st.divider()

        # Category Bar Chart
        st.subheader("Category Spend vs Budget Comparison")
        cat_comparison = []
        for cat in categories:
            cat_rollover = cat_prev_savings.get(cat["id"], 0.0) if enable_rollover else 0.0
            st_data = db.get_category_monthly_stats(cat["id"], year_choice, selected_month, cat_rollover)
            if st_data:
                cat_comparison.append({
                    "Category": f"{cat['icon']} {cat['name']}",
                    "Type": "Spent",
                    "Amount (₹)": st_data["total_spent"]
                })
                cat_comparison.append({
                    "Category": f"{cat['icon']} {cat['name']}",
                    "Type": "Budget",
                    "Amount (₹)": st_data["effective_budget"]
                })

        if cat_comparison:
            df_cat = pd.DataFrame(cat_comparison)
            bar_chart = alt.Chart(df_cat).mark_bar().encode(
                x=alt.X("Category:N", title="Category"),
                y=alt.Y("Amount (₹):Q", title="Amount (₹)"),
                color=alt.Color("Type:N", scale=alt.Scale(domain=["Spent", "Budget"], range=["#f97316", "#3b82f6"])),
                xOffset="Type:N",
                tooltip=["Category:N", "Type:N", "Amount (₹):Q"]
            ).properties(height=300)

            st.altair_chart(bar_chart, width="stretch")

# ----------------- TAB 4: CATEGORIES & SHORTCUTS -----------------
with tab_categories:
    st.subheader("Configured Categories & Rule Tuning")
    st.caption("Modify limits, frequency, or delete unwanted categories:")

    for cat in categories:
        with st.expander(f"{cat['icon']} {cat['name']} — Rules & Edit", expanded=False):
            cat_rollover = cat_prev_savings.get(cat["id"], 0.0) if enable_rollover else 0.0
            stats = db.get_category_monthly_stats(cat["id"], year_choice, selected_month, cat_rollover)
            colA, colB = st.columns(2)
            with colA:
                with st.form(f"edit_cat_{cat['id']}"):
                    e_name = st.text_input("Category Name", value=cat["name"])
                    e_icon = st.text_input("Emoji Icon", value=cat["icon"])
                    e_limit = st.number_input("Target Limit per Spend (₹)", min_value=1.0, value=float(cat["limit_per_time"]), step=10.0)
                    e_freq = st.number_input("Frequency per Month", min_value=1, value=int(cat["frequency_per_month"]), step=1)
                    save_edit = st.form_submit_button("Update Category Rule")
                    if save_edit:
                        ok, msg = db.update_category(cat["id"], e_name, e_limit, e_freq, e_icon)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            with colB:
                st.write("**Month Status Breakdown:**")
                st.write(f"- Base Monthly Budget: **₹{cat['monthly_budget']:,.2f}**")
                if cat_rollover > 0:
                    st.write(f"- Rolled Over Savings: **+₹{cat_rollover:,.2f}**")
                st.write(f"- Effective Total Budget: **₹{stats['effective_budget']:,.2f}**")
                st.write(f"- Total Spent So Far: **₹{stats['total_spent']:,.2f}**")
                st.write(f"- Spends Logged: **{stats['spends_done']} / {cat['frequency_per_month']}**")
                st.write(f"- Average Spent Per Transaction: **₹{stats['actual_avg']:,.2f}**")
                st.write(f"- Allowed Average for Next Spends: **₹{stats['recommended_next_avg']:,.2f}**")
                
                if st.button(f"🗑️ Delete Category: {cat['name']}", key=f"del_{cat['id']}"):
                    db.delete_category(cat["id"])
                    st.success("Category deleted.")
                    st.rerun()

    st.divider()
    # Manage 1-Tap Quick Buttons
    st.subheader("⚡ Manage 1-Tap Quick Add Shortcuts")
    st.caption("Create quick buttons for frequent transactions (e.g. 'Chai ₹20', 'Auto ₹50', 'Snack ₹100')")

    col_t1, col_t2 = st.columns([1, 1])
    with col_t1:
        st.write("**Create New 1-Tap Button**")
        with st.form("add_template_form", clear_on_submit=True):
            if categories:
                t_cat_opts = {f"{c['icon']} {c['name']}": c["id"] for c in categories}
                t_cat_choice = st.selectbox("Category", list(t_cat_opts.keys()))
                t_label = st.text_input("Button Label (e.g. Chai, Auto, Groceries)")
                t_amount = st.number_input("Amount (₹)", min_value=1.0, value=50.0, step=10.0)
                t_icon = st.text_input("Button Icon Emoji", value="⚡")
                t_save = st.form_submit_button("Add Quick Button", width="stretch")
                if t_save:
                    if t_label.strip():
                        db.add_quick_template(t_cat_opts[t_cat_choice], t_label, t_amount, t_icon)
                        st.success(f"Added shortcut '{t_label}'!")
                        st.rerun()
                    else:
                        st.warning("Please provide a label.")

    with col_t2:
        st.write("**Existing Quick Buttons**")
        templates_list = db.get_quick_templates()
        if not templates_list:
            st.info("No shortcuts created yet.")
        else:
            for tmpl in templates_list:
                row_c1, row_c2 = st.columns([3, 1])
                with row_c1:
                    st.write(f"{tmpl['icon']} **{tmpl['label']}** — ₹{tmpl['amount']:.0f} *({tmpl['category_name']})*")
                with row_c2:
                    if st.button("Delete", key=f"del_tmpl_{tmpl['id']}"):
                        db.delete_quick_template(tmpl["id"])
                        st.rerun()

# ----------------- TAB 5: HISTORY & DELETE -----------------
with tab_history:
    st.subheader(f"📜 Transaction Log for {month_choice_name} {year_choice}")
    expenses = db.get_monthly_expenses(year_choice, selected_month)
    
    if not expenses:
        st.info("No expenses logged for this month yet.")
    else:
        df = pd.DataFrame([{
            "ID": e["id"],
            "Date": e["date"],
            "Category": f"{e['icon']} {e['category_name']}",
            "Amount (₹)": e["amount"],
            "Target Limit (₹)": e["limit_per_time"],
            "Variance": f"+₹{e['amount'] - e['limit_per_time']:.2f}" if e['amount'] > e['limit_per_time'] else f"-₹{e['limit_per_time'] - e['amount']:.2f}",
            "Status": "⚠️ Exceeded" if e['amount'] > e['limit_per_time'] else "✅ Within Limit",
            "Note": e["note"]
        } for e in expenses])

        st.dataframe(df, width="stretch")

        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Monthly Expenses (CSV)",
            data=csv_data,
            file_name=f"expenses_{year_choice}_{selected_month:02d}.csv",
            mime="text/csv",
        )

        st.write("---")
        st.subheader("🗑️ Delete a Transaction")
        
        # Friendly selection formatted with date, category and amount
        del_options = {}
        for e in expenses:
            note_str = f" ({e['note']})" if e['note'] else ""
            label = f"#{e['id']} | {e['date']} | {e['icon']} {e['category_name']} | ₹{e['amount']:,.2f}{note_str}"
            del_options[label] = e['id']
        selected_del_label = st.selectbox("Select expense to delete", list(del_options.keys()))
        selected_del_id = del_options[selected_del_label]
        
        if st.button("Delete Selected Transaction", type="secondary"):
            db.delete_expense(selected_del_id)
            st.toast(f"Deleted transaction #{selected_del_id}!", icon="🗑️")
            st.rerun()

# ----------------- TAB 6: RESET PROVISIONS -----------------
with tab_reset:
    st.subheader("🔄 Expense Reset Provisions")
    st.caption("Safely reset or clear logged expenses. Your categories and budget rules will remain intact.")

    r_col1, r_col2, r_col3 = st.columns(3)

    # 1. Weekly Reset
    with r_col1:
        st.markdown("""
        <div class="stat-card">
            <h4>📅 Weekly Reset</h4>
            <p style="color:#64748b; font-size:0.88rem;">Clear all expenses logged for the current active week (Monday to Sunday).</p>
        </div>
        """, unsafe_allow_html=True)
        confirm_week = st.checkbox("Confirm weekly reset", key="conf_week")
        if st.button("Reset Current Week", type="secondary", width="stretch", disabled=not confirm_week):
            cnt, s_date, e_date = db.reset_expenses_weekly()
            st.toast(f"Deleted {cnt} expenses from {s_date} to {e_date}!", icon="🔄")
            st.rerun()

    # 2. Monthly Reset
    with r_col2:
        st.markdown(f"""
        <div class="stat-card">
            <h4>🗓️ Monthly Reset</h4>
            <p style="color:#64748b; font-size:0.88rem;">Clear all expenses for <strong>{month_choice_name} {year_choice}</strong>.</p>
        </div>
        """, unsafe_allow_html=True)
        confirm_month = st.checkbox("Confirm monthly reset", key="conf_month")
        if st.button(f"Reset {month_choice_name} {year_choice}", type="secondary", width="stretch", disabled=not confirm_month):
            cnt = db.reset_expenses_monthly(year_choice, selected_month)
            st.toast(f"Deleted {cnt} expenses for {month_choice_name} {year_choice}!", icon="🔄")
            st.rerun()

    # 3. All Time Reset
    with r_col3:
        st.markdown("""
        <div class="stat-card">
            <h4 style="color:#dc2626;">⚠️ All-Time Reset</h4>
            <p style="color:#64748b; font-size:0.88rem;">Clear all recorded expenses across all months and years.</p>
        </div>
        """, unsafe_allow_html=True)
        confirm_all = st.checkbox("Confirm ALL-TIME wipe", key="conf_all")
        if st.button("Wipe All Expenses", type="primary", width="stretch", disabled=not confirm_all):
            cnt = db.reset_expenses_all_time()
            st.toast(f"All {cnt} expenses cleared!", icon="🧹")
            st.rerun()
