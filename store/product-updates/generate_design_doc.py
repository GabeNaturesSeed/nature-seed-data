#!/usr/bin/env python3
"""
Generate Google Ads API Design Documentation PDF for Nature's Seed.
"""

from fpdf import FPDF
from datetime import date


class DesignDoc(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, "Nature's Seed - Google Ads API Tool Design Documentation", align="R")
            self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(45, 106, 79)  # Brand green
        self.cell(0, 10, title)
        self.ln(6)
        # Underline
        self.set_draw_color(45, 106, 79)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(6)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(27, 67, 50)  # Brand dark green
        self.cell(0, 8, title)
        self.ln(6)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(51, 51, 51)
        self.multi_cell(0, 5.5, text)
        self.ln(3)

    def bullet_point(self, text, indent=10):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(51, 51, 51)
        x = self.get_x()
        self.set_x(x + indent)
        self.cell(4, 5.5, chr(183))
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bold_bullet(self, bold_part, rest, indent=10):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(51, 51, 51)
        x = self.get_x()
        self.set_x(x + indent)
        self.cell(4, 5.5, chr(183))
        self.set_font("Helvetica", "B", 10)
        self.cell(self.get_string_width(bold_part) + 1, 5.5, bold_part)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, rest)
        self.ln(1)

    def table_row(self, cells, widths, bold=False, header=False):
        if header:
            self.set_font("Helvetica", "B", 9)
            self.set_fill_color(45, 106, 79)
            self.set_text_color(255, 255, 255)
        elif bold:
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(51, 51, 51)
            self.set_fill_color(245, 245, 245)
        else:
            self.set_font("Helvetica", "", 9)
            self.set_text_color(51, 51, 51)
            self.set_fill_color(255, 255, 255)

        for i, (cell, w) in enumerate(zip(cells, widths)):
            self.cell(w, 7, cell, border=1, fill=True)
        self.ln()


def build_pdf():
    pdf = DesignDoc()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # =========================================================
    # COVER / TITLE
    # =========================================================
    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(45, 106, 79)
    pdf.cell(0, 14, "Nature's Seed", align="C")
    pdf.ln(14)

    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(0, 10, "Google Ads API Tool", align="C")
    pdf.ln(8)
    pdf.cell(0, 10, "Design Documentation", align="C")
    pdf.ln(20)

    pdf.set_draw_color(45, 106, 79)
    pdf.set_line_width(1)
    mid = pdf.w / 2
    pdf.line(mid - 40, pdf.get_y(), mid + 40, pdf.get_y())
    pdf.ln(15)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, "Company: Nature's Seed LLC", align="C")
    pdf.ln(7)
    pdf.cell(0, 7, "Website: https://www.naturesseed.com", align="C")
    pdf.ln(7)
    pdf.cell(0, 7, "Contact: gabe@naturesseed.com", align="C")
    pdf.ln(7)
    pdf.cell(0, 7, f"Date: {date.today().strftime('%B %d, %Y')}", align="C")
    pdf.ln(7)
    pdf.cell(0, 7, "Version: 1.0", align="C")
    pdf.ln(30)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 6, "This document describes Nature's Seed's internal tool that uses the Google Ads API", align="C")
    pdf.ln(5)
    pdf.cell(0, 6, "for campaign management, reporting, and performance optimization.", align="C")

    # =========================================================
    # PAGE 2: TABLE OF CONTENTS
    # =========================================================
    pdf.add_page()
    pdf.section_title("Table of Contents")
    pdf.ln(3)

    toc = [
        ("1.", "Company Overview"),
        ("2.", "Tool Overview & Purpose"),
        ("3.", "Google Ads API Use Cases"),
        ("4.", "Technical Architecture"),
        ("5.", "Data Flow & Integration Map"),
        ("6.", "Features & Functionality"),
        ("7.", "User Interface & Access"),
        ("8.", "Data Security & Compliance"),
        ("9.", "API Usage Estimates"),
        ("10.", "Appendix: Connected Systems"),
    ]
    for num, title in toc:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(12, 8, num)
        pdf.cell(0, 8, title)
        pdf.ln(8)

    # =========================================================
    # SECTION 1: COMPANY OVERVIEW
    # =========================================================
    pdf.add_page()
    pdf.section_title("1. Company Overview")

    pdf.body_text(
        "Nature's Seed is a premium seed company based in Lehi, Utah, specializing in high-quality "
        "grass seed, pasture seed, wildflower seed, and specialty seed products for residential, "
        "agricultural, and conservation markets across the United States."
    )

    pdf.sub_title("Company Details")
    details = [
        ["Company Name", "Nature's Seed LLC"],
        ["Website", "https://www.naturesseed.com"],
        ["Industry", "Ecommerce / Agriculture / Garden"],
        ["Location", "1697 W 2100 N, Lehi, UT 84043"],
        ["Primary Platform", "WooCommerce (self-hosted)"],
        ["Secondary Channel", "Walmart Marketplace"],
        ["Product Count", "250+ SKUs across 8 major categories"],
    ]
    widths = [55, 120]
    pdf.table_row(["Field", "Value"], widths, header=True)
    for row in details:
        pdf.table_row(row, widths)
    pdf.ln(5)

    pdf.body_text(
        "Nature's Seed sells directly to consumers through its WooCommerce storefront and through "
        "Walmart Marketplace. The company manages inventory through Fishbowl WMS and runs email "
        "marketing through Klaviyo. The Google Ads API integration will complete the data loop by "
        "connecting advertising spend and performance data to sales and inventory systems."
    )

    # =========================================================
    # SECTION 2: TOOL OVERVIEW
    # =========================================================
    pdf.add_page()
    pdf.section_title("2. Tool Overview & Purpose")

    pdf.body_text(
        "Nature's Seed is building an internal Data Orchestrator tool that unifies data across all "
        "business systems into a single operational hub. The tool is used exclusively by Nature's Seed "
        "employees and is not offered to external clients or third parties."
    )

    pdf.sub_title("Tool Name")
    pdf.body_text("Nature's Seed Data Orchestrator")

    pdf.sub_title("Purpose")
    pdf.body_text(
        "The Data Orchestrator aggregates data from all connected platforms (WooCommerce, Walmart, "
        "Klaviyo, Fishbowl, and Google Ads) to provide a unified view of business performance. "
        "By integrating Google Ads data, the tool enables the team to:"
    )

    pdf.bullet_point("Track advertising spend alongside revenue data from WooCommerce and Walmart")
    pdf.bullet_point("Calculate true ROAS (Return on Ad Spend) by matching ad clicks to actual orders")
    pdf.bullet_point("Identify overspending on underperforming campaigns or product categories")
    pdf.bullet_point("Detect underspending on high-converting products that could benefit from more budget")
    pdf.bullet_point("Generate actionable optimization recommendations based on cross-platform data")
    pdf.bullet_point("Report on full-funnel performance from ad impression to completed sale")

    pdf.ln(3)
    pdf.sub_title("Who Uses This Tool")
    pdf.body_text(
        "This is an internal-only tool used by Nature's Seed's marketing team and leadership. "
        "There are no external users, no third-party access, and no plans to commercialize the tool. "
        "The tool is accessed by 2-5 internal team members."
    )

    pdf.sub_title("Tool Type")
    pdf.body_text(
        "Internal tool for personal use (managing Nature's Seed's own Google Ads account only). "
        "This tool will only access Nature's Seed's own Google Ads manager account and the client "
        "accounts within it. It does not manage ads for other businesses."
    )

    # =========================================================
    # SECTION 3: GOOGLE ADS API USE CASES
    # =========================================================
    pdf.add_page()
    pdf.section_title("3. Google Ads API Use Cases")

    pdf.body_text("The tool will use the Google Ads API for the following specific purposes:")

    pdf.ln(2)
    pdf.sub_title("3.1 Reporting & Analytics (Primary Use)")
    pdf.body_text(
        "The primary use of the Google Ads API is to pull campaign performance data and join it "
        "with revenue data from WooCommerce and Walmart for holistic reporting."
    )
    pdf.bullet_point("Pull campaign-level metrics: impressions, clicks, cost, conversions, CTR, CPC")
    pdf.bullet_point("Pull ad group and keyword-level performance data")
    pdf.bullet_point("Pull product-level Shopping campaign performance (product partition reports)")
    pdf.bullet_point("Match Google Ads conversion data to actual WooCommerce/Walmart orders")
    pdf.bullet_point("Calculate blended ROAS across advertising and organic channels")
    pdf.bullet_point("Generate daily, weekly, and monthly performance summaries")

    pdf.ln(2)
    pdf.sub_title("3.2 Campaign Management (Secondary Use)")
    pdf.body_text(
        "The tool will provide campaign management capabilities to enable data-driven budget "
        "and bid adjustments based on cross-platform performance insights."
    )
    pdf.bullet_point("Adjust campaign budgets based on inventory availability (pause ads for out-of-stock items)")
    pdf.bullet_point("Modify bids based on product profitability data from WooCommerce")
    pdf.bullet_point("Pause/enable campaigns or ad groups based on seasonal product availability")
    pdf.bullet_point("Update product feeds for Shopping campaigns when catalog changes occur")

    pdf.ln(2)
    pdf.sub_title("3.3 Optimization Insights")
    pdf.body_text(
        "By combining Google Ads data with sales, inventory, and email marketing data, the tool "
        "generates optimization recommendations:"
    )
    pdf.bullet_point("Flag campaigns spending above target CPA with low conversion rates")
    pdf.bullet_point("Identify high-margin products with low ad spend (underspending opportunities)")
    pdf.bullet_point("Recommend budget reallocation from low-ROAS to high-ROAS campaigns")
    pdf.bullet_point("Alert when advertised products are going out of stock in Fishbowl")
    pdf.bullet_point("Suggest new keyword opportunities based on organic search and product category trends")

    # =========================================================
    # SECTION 4: TECHNICAL ARCHITECTURE
    # =========================================================
    pdf.add_page()
    pdf.section_title("4. Technical Architecture")

    pdf.sub_title("System Components")
    pdf.body_text("The Data Orchestrator is built with the following components:")

    pdf.ln(2)
    components = [
        ["Component", "Technology", "Purpose"],
        ["Orchestrator Core", "Python 3.x", "Central data aggregation and logic"],
        ["API Connectors", "REST / OAuth 2.0", "Connect to Google Ads, WooCommerce, etc."],
        ["Data Storage", "Local JSON / CSV", "Cache reports and cross-reference data"],
        ["Headless Storefront", "Next.js 16 / React", "Customer-facing store (naturesseed.com)"],
        ["Ecommerce Backend", "WooCommerce (WP)", "Order processing, product catalog"],
        ["Inventory (WMS)", "Fishbowl", "Warehouse stock management"],
        ["Email Marketing", "Klaviyo", "Customer flows, segments, campaigns"],
        ["Marketplace", "Walmart API", "Secondary sales channel"],
        ["Payments", "Stripe", "Payment processing"],
    ]
    widths_3 = [45, 45, 85]
    pdf.table_row(components[0], widths_3, header=True)
    for row in components[1:]:
        pdf.table_row(row, widths_3)

    pdf.ln(5)
    pdf.sub_title("Google Ads API Integration Details")

    api_details = [
        ["Setting", "Value"],
        ["API Version", "Google Ads API v18+ (latest stable)"],
        ["Auth Method", "OAuth 2.0 (Service Account or Web App flow)"],
        ["Client Library", "google-ads-python (official Google client)"],
        ["Account Type", "Manager Account (MCC)"],
        ["Access Scope", "Nature's Seed accounts only"],
        ["Data Direction", "Primarily read (reports); limited write (budgets/bids)"],
        ["Refresh Rate", "Daily batch pulls; on-demand for alerts"],
    ]
    widths_2 = [55, 120]
    pdf.table_row(api_details[0], widths_2, header=True)
    for row in api_details[1:]:
        pdf.table_row(row, widths_2)

    # =========================================================
    # SECTION 5: DATA FLOW
    # =========================================================
    pdf.add_page()
    pdf.section_title("5. Data Flow & Integration Map")

    pdf.body_text(
        "The Data Orchestrator sits at the center of all Nature's Seed systems, pulling data from "
        "each platform and correlating it for unified reporting and actionable insights."
    )

    pdf.ln(3)
    pdf.sub_title("Data Flow Overview")
    pdf.ln(2)

    # Text-based architecture diagram
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(51, 51, 51)
    diagram = [
        "+------------------+     +-------------------+     +------------------+",
        "|   Google Ads     |     |    WooCommerce     |     | Walmart Mktp     |",
        "|  (Ad Spend &     |     |  (Orders, Revenue, |     | (Orders, Revenue |",
        "|   Performance)   |     |   Products, Cust.) |     |  Listings)       |",
        "+--------+---------+     +---------+----------+     +--------+---------+",
        "         |                         |                          |",
        "         v                         v                          v",
        "+--------+-------------------------+------------+-------------+--------+",
        "|                                                                      |",
        "|                   NATURE'S SEED DATA ORCHESTRATOR                     |",
        "|                                                                      |",
        "|   - Cross-platform ROAS calculation                                  |",
        "|   - Spend vs Revenue matching                                        |",
        "|   - Inventory-aware ad management                                    |",
        "|   - Campaign optimization recommendations                            |",
        "|                                                                      |",
        "+--------+-------------------------+------------+-------------+--------+",
        "         |                         |                          |",
        "         v                         v                          v",
        "+--------+---------+     +---------+----------+     +--------+---------+",
        "|    Fishbowl      |     |      Klaviyo       |     |     Stripe       |",
        "|  (Inventory &    |     |  (Email Marketing, |     |  (Payment        |",
        "|   Warehouse)     |     |   Segments, Flows) |     |   Processing)    |",
        "+------------------+     +--------------------+     +------------------+",
    ]
    for line in diagram:
        pdf.cell(0, 4, line)
        pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.ln(5)
    pdf.sub_title("Google Ads Data Used")

    data_used = [
        ["Data Point", "API Resource", "Used For"],
        ["Campaign metrics", "GoogleAdsService (campaign)", "Spend tracking, ROAS"],
        ["Ad group metrics", "GoogleAdsService (ad_group)", "Granular performance"],
        ["Keyword performance", "GoogleAdsService (keyword_view)", "Search term analysis"],
        ["Shopping products", "GoogleAdsService (shopping_perf.)", "Product-level ROAS"],
        ["Conversion tracking", "GoogleAdsService (conversion)", "Revenue attribution"],
        ["Budget data", "CampaignBudget resource", "Budget vs actual spend"],
        ["Campaign status", "Campaign resource", "Pause/enable automation"],
    ]
    widths_3b = [42, 55, 78]
    pdf.table_row(data_used[0], widths_3b, header=True)
    for row in data_used[1:]:
        pdf.table_row(row, widths_3b)

    # =========================================================
    # SECTION 6: FEATURES & FUNCTIONALITY
    # =========================================================
    pdf.add_page()
    pdf.section_title("6. Features & Functionality")

    pdf.sub_title("6.1 Unified Performance Dashboard")
    pdf.body_text(
        "Combines Google Ads spend data with WooCommerce and Walmart revenue to calculate true "
        "cross-channel ROAS. Shows daily/weekly/monthly trends with the ability to drill down to "
        "campaign, ad group, product, or keyword level."
    )

    pdf.sub_title("6.2 Campaign-to-Revenue Matching")
    pdf.body_text(
        "Matches Google Ads campaign conversions against actual fulfilled orders in WooCommerce. "
        "This eliminates discrepancies between Google's reported conversions and real revenue, "
        "providing a ground-truth ROAS number."
    )

    pdf.sub_title("6.3 Overspend / Underspend Alerts")
    pdf.body_text(
        "Automatically flags campaigns that are:"
    )
    pdf.bold_bullet("Overspending: ", "High ad spend but low conversion rate or low order value relative to spend. "
                    "For example, a campaign spending $50/day on a product with $10 margin and only 1 sale/day.")
    pdf.bold_bullet("Underspending: ", "Products with high organic conversion rates, high margins, or strong "
                    "Klaviyo email engagement but minimal or no ad spend allocated to them.")

    pdf.ln(2)
    pdf.sub_title("6.4 Inventory-Aware Campaign Management")
    pdf.body_text(
        "Cross-references Fishbowl inventory data with active Google Ads campaigns. When a product "
        "goes out of stock in the warehouse, the tool can automatically pause the corresponding "
        "ad campaigns to avoid wasting spend on products that cannot be fulfilled. When stock is "
        "replenished, campaigns are re-enabled."
    )

    pdf.sub_title("6.5 Product-Level Profitability Analysis")
    pdf.body_text(
        "For each product SKU, the tool calculates:"
    )
    pdf.bullet_point("Google Ads spend attributed to that product")
    pdf.bullet_point("Revenue from WooCommerce + Walmart orders for that product")
    pdf.bullet_point("Gross margin (revenue minus product cost and shipping)")
    pdf.bullet_point("Net ROAS after accounting for all costs")
    pdf.bullet_point("Recommended budget allocation based on profitability")

    pdf.ln(2)
    pdf.sub_title("6.6 Cross-Channel Customer Journey Insights")
    pdf.body_text(
        "Combines Google Ads click data with Klaviyo email engagement data to understand the full "
        "customer journey. For example, identifying customers who clicked a Google Ad, received "
        "a welcome email series via Klaviyo, and then converted through an abandoned cart email."
    )

    # =========================================================
    # SECTION 7: USER INTERFACE
    # =========================================================
    pdf.add_page()
    pdf.section_title("7. User Interface & Access")

    pdf.sub_title("Access Model")
    pdf.body_text(
        "The tool is accessed through a command-line interface and automated scripts run by "
        "Nature's Seed's internal team. There is no public-facing web interface. Reports are "
        "generated as structured data (JSON/CSV) and can be viewed in spreadsheet tools or "
        "business intelligence dashboards."
    )

    pdf.sub_title("Users")

    users = [
        ["Role", "Access Level", "Usage"],
        ["Marketing Manager", "Full read + write", "Daily campaign review, budget adjustments"],
        ["CEO / Leadership", "Read-only reports", "Weekly/monthly performance summaries"],
        ["Data Analyst", "Full read + write", "Custom queries, optimization analysis"],
    ]
    widths_3c = [45, 45, 85]
    pdf.table_row(users[0], widths_3c, header=True)
    for row in users[1:]:
        pdf.table_row(row, widths_3c)

    pdf.ln(5)
    pdf.sub_title("Sample Output: Overspend/Underspend Report")
    pdf.ln(2)
    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(51, 51, 51)
    report_lines = [
        "+------+-----------------------------+----------+---------+-------+--------+-----------+",
        "| Flag | Campaign                    | Spend/mo | Revenue | ROAS  | Stock  | Action    |",
        "+------+-----------------------------+----------+---------+-------+--------+-----------+",
        "| OVER | Pasture Seed - Broad Match  | $1,200   | $890    | 0.74x | 45 qty | Cut 40%   |",
        "| OVER | Wildflower - Display        | $650     | $210    | 0.32x | 12 qty | Pause     |",
        "| GOOD | Lawn Seed - Northern        | $800     | $3,400  | 4.25x | 80 qty | Maintain  |",
        "| UNDR | CA Native Wildflower - Shop | $50      | $1,800  | 36.0x | 60 qty | Scale 5x  |",
        "| UNDR | Clover Seed - Brand         | $0       | $2,100  | n/a   | 90 qty | Start ads |",
        "+------+-----------------------------+----------+---------+-------+--------+-----------+",
    ]
    for line in report_lines:
        pdf.cell(0, 3.8, line)
        pdf.ln(3.8)

    pdf.set_font("Helvetica", "", 10)
    pdf.ln(5)
    pdf.body_text(
        "The report above shows how the tool combines Google Ads spend with WooCommerce revenue "
        "and Fishbowl inventory to generate actionable recommendations. Overspending campaigns "
        "are flagged for budget reduction, while underspending products with strong organic "
        "performance are flagged for ad investment."
    )

    # =========================================================
    # SECTION 8: SECURITY
    # =========================================================
    pdf.add_page()
    pdf.section_title("8. Data Security & Compliance")

    pdf.sub_title("8.1 Authentication & Authorization")
    pdf.body_text(
        "All Google Ads API access uses OAuth 2.0 authentication. API credentials (client ID, "
        "client secret, refresh tokens) are stored in environment variables on secure local "
        "machines. Credentials are never hardcoded in source code or committed to version control."
    )

    pdf.sub_title("8.2 Data Encryption")
    pdf.bullet_point("All API communications use TLS 1.2+ (HTTPS) encryption in transit")
    pdf.bullet_point("API credentials are stored in .env files excluded from version control via .gitignore")
    pdf.bullet_point("No Google Ads data is transmitted to third parties")
    pdf.bullet_point("All data is processed on secure, access-controlled local infrastructure")

    pdf.ln(2)
    pdf.sub_title("8.3 Data Retention & Privacy")
    pdf.bullet_point("Performance data is retained for internal reporting purposes only")
    pdf.bullet_point("No personally identifiable information (PII) is extracted from Google Ads")
    pdf.bullet_point("The tool does not store or process end-user (customer) data from Google Ads")
    pdf.bullet_point("All data handling complies with Google's API Terms of Service")

    pdf.ln(2)
    pdf.sub_title("8.4 Access Control")
    pdf.bullet_point("Tool access is restricted to Nature's Seed employees only (2-5 users)")
    pdf.bullet_point("Each user authenticates with individual credentials")
    pdf.bullet_point("Google Ads account access is limited to Nature's Seed's own MCC and client accounts")
    pdf.bullet_point("No third-party access to the tool or the data it processes")

    # =========================================================
    # SECTION 9: API USAGE
    # =========================================================
    pdf.add_page()
    pdf.section_title("9. API Usage Estimates")

    pdf.body_text(
        "Nature's Seed runs a modest Google Ads program focused on seed products. "
        "API usage will be well within Basic Access limits."
    )

    pdf.ln(2)
    usage = [
        ["Operation", "Frequency", "Est. Daily Calls"],
        ["Campaign performance reports", "Daily batch pull", "5-10"],
        ["Ad group performance reports", "Daily batch pull", "10-20"],
        ["Keyword performance reports", "Daily batch pull", "10-20"],
        ["Shopping product reports", "Daily batch pull", "5-10"],
        ["Budget reads/updates", "On-demand", "2-5"],
        ["Campaign status updates", "On-demand (inventory)", "1-5"],
        ["Account hierarchy reads", "Weekly", "1-2"],
        ["", "TOTAL ESTIMATED", "34-72 / day"],
    ]
    widths_3d = [55, 50, 70]
    pdf.table_row(usage[0], widths_3d, header=True)
    for row in usage[1:-1]:
        pdf.table_row(row, widths_3d)
    pdf.table_row(usage[-1], widths_3d, bold=True)

    pdf.ln(5)
    pdf.body_text(
        "These estimates are well within the Basic Access limit of 15,000 operations per day. "
        "The tool prioritizes batch operations to minimize API calls and uses local caching "
        "to avoid redundant requests."
    )

    # =========================================================
    # SECTION 10: APPENDIX
    # =========================================================
    pdf.add_page()
    pdf.section_title("10. Appendix: Connected Systems")

    pdf.body_text(
        "The following systems are currently connected to the Nature's Seed Data Orchestrator. "
        "Google Ads will be integrated as an additional data source alongside these existing connections."
    )

    pdf.ln(2)
    systems = [
        ["System", "Connection", "Data", "Status"],
        ["WooCommerce", "REST API v3", "Products, orders, customers", "Active"],
        ["Walmart Mktp", "OAuth 2.0 API", "Listings, orders, inventory", "Active"],
        ["Klaviyo", "REST API + MCP", "Email flows, segments, metrics", "Active"],
        ["Fishbowl WMS", "REST API", "Inventory, SKUs, warehouses", "Active"],
        ["Stripe", "Via WooCommerce", "Payment processing", "Active"],
        ["Google Ads", "Google Ads API", "Campaigns, spend, conversions", "Pending"],
    ]
    widths_4 = [35, 38, 62, 30]
    pdf.table_row(systems[0], widths_4, header=True)
    for row in systems[1:]:
        pdf.table_row(row, widths_4)

    pdf.ln(8)
    pdf.sub_title("Product Categories Advertised")
    pdf.body_text("Nature's Seed advertises products across these main categories:")

    categories = [
        "Lawn Seed (Northern, Southern, Transitional, Water-Wise, Sports Turf)",
        "Pasture Seed (Horse, Cattle, Goat, Sheep, Alpaca - 40+ products)",
        "Native Wildflower Seed (Regional mixes - 22 products)",
        "California Collection (Native, fire-resistant, erosion control - 24 products)",
        "Clover Seed (6 products)",
        "Specialty Seed (Food plot, cover crop - 34 products)",
        "Planting Aids (Tackifier, mulch - 5 products)",
    ]
    for cat in categories:
        pdf.bullet_point(cat)

    pdf.ln(8)
    pdf.set_draw_color(45, 106, 79)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "End of Document", align="C")
    pdf.ln(5)
    pdf.cell(0, 6, "Nature's Seed LLC | 1697 W 2100 N, Lehi, UT 84043 | naturesseed.com", align="C")

    # Save
    output_path = "Nature_s_Seed_Google_Ads_API_Design_Documentation.pdf"
    pdf.output(output_path)
    print(f"PDF saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    build_pdf()
