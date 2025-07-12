import datetime
import io
import os
import textwrap
from collections import defaultdict
from dotenv import load_dotenv
from fpdf import FPDF, XPos, YPos
import matplotlib
import matplotlib.pyplot as plt
import requests
from groq import Groq
import urllib.request

# Use a non-interactive backend for Matplotlib
matplotlib.use('Agg')

# Load environment variables
load_dotenv()

# --- Report Styling Constants ---
PRIMARY_COLOR = (6, 40, 92)      # MSRIT Blue
SECONDARY_COLOR = (34, 34, 34)   # Dark Grey (changed from red)
TEXT_COLOR = (34, 34, 34)        # Dark Grey
BG_COLOR_LIGHT = (245, 245, 245) # Light background for tables
FONT_FAMILY = "DejaVu"
RUPEE_SYMBOL = "₹"

# --- Font Handling ---
def setup_fonts(pdf):
    """Checks for local DejaVu fonts and adds them to FPDF."""
    global FONT_FAMILY, RUPEE_SYMBOL
    font_dir = "fonts"
    font_files = {
        'DejaVu': os.path.join(font_dir, 'DejaVuSans.ttf'),
        'DejaVuB': os.path.join(font_dir, 'DejaVuSans-Bold.ttf'),
    }

    # Check for local fonts
    if not os.path.exists(font_files['DejaVu']) or not os.path.exists(font_files['DejaVuB']):
        print("--- FONT WARNING ---")
        print(f"'{font_files['DejaVu']}' or '{font_files['DejaVuB']}' not found.")
        print("Falling back to Arial/Helvetica. Report may have formatting issues.")
        FONT_FAMILY = "Arial"
        RUPEE_SYMBOL = "Rs."
        # Set Matplotlib to use standard fonts
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
        return

    try:
        pdf.add_font(FONT_FAMILY, '', font_files['DejaVu'])
        pdf.add_font(FONT_FAMILY, 'B', font_files['DejaVuB'])
        # Set font for matplotlib - use system fonts instead of custom
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
        print("✅ DejaVu fonts loaded successfully for PDF.")
    except Exception as e:
        print(f"Could not add font to FPDF. Error: {e}")
        FONT_FAMILY = "Arial"
        RUPEE_SYMBOL = "Rs."
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica']

class PDF(FPDF):
    """Custom PDF class with Header, Footer, and enhanced content methods."""
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font(FONT_FAMILY, 'B', 9)
        self.set_text_color(*PRIMARY_COLOR)
        self.cell(0, 10, 'Comprehensive Asset Management Report', 0, 0, 'L')
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')
        self.ln(15)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font(FONT_FAMILY, '', 8)
        self.set_text_color(128)
        self.cell(0, 10, 'Generated for M.S. Ramaiah Institute of Technology', 0, 0, 'C')

    def cover_page(self):
        self.add_page()
        self.set_fill_color(*PRIMARY_COLOR)
        self.rect(0, 0, 210, 297, 'F')
        self.set_font(FONT_FAMILY, 'B', 24)
        self.set_text_color(255, 255, 255)
        self.set_y(100)
        self.multi_cell(0, 15, 'Comprehensive Asset Management Report', align='C')
        self.set_font(FONT_FAMILY, 'B', 18)
        self.set_y(130)
        self.cell(0, 15, 'M.S. Ramaiah Institute of Technology', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font(FONT_FAMILY, '', 12)
        self.set_y(250)
        self.cell(0, 10, f"Report Generated: {datetime.datetime.now().strftime('%B %d, %Y')}", align='C')

    def chapter_title(self, title, level=1):
        if level == 1:
            self.set_font(FONT_FAMILY, 'B', 16)
            self.set_text_color(*PRIMARY_COLOR)
            self.cell(0, 10, title, 0, 1, 'L')
            self.ln(5)
        elif level == 2:
            self.set_font(FONT_FAMILY, 'B', 12)
            self.set_text_color(*SECONDARY_COLOR)
            self.cell(0, 8, title, 0, 1, 'L')
            self.ln(2)

    def write_ai_summary(self, ai_content):
        self.chapter_title("AI-Powered Analysis")
        self.set_font(FONT_FAMILY, '', 10)
        self.set_text_color(*TEXT_COLOR)
        
        sections = ai_content.split('### ')
        for section in sections:
            if not section.strip(): 
                continue
                
            lines = section.split('\n')
            if not lines:
                continue
                
            title = lines[0].strip()
            body_lines = lines[1:] if len(lines) > 1 else []
            
            # Handle section title
            if title:
                self.chapter_title(title, level=2)
            
            # Process body content
            for line in body_lines:
                line = line.strip()
                if not line:
                    self.ln(4)  # Add space for empty lines
                    continue
                    
                # Handle bullet points
                if line.startswith('- '):
                    self.set_x(15)
                    self.cell(5, 5, '•')
                    self.set_x(20)
                    text = line[2:].strip()
                    # Handle bold text in bullet points
                    if '**' in text:
                        parts = text.split('**')
                        for i, part in enumerate(parts):
                            if i % 2 == 1:  # Odd indices are bold
                                self.set_font(FONT_FAMILY, 'B', 10)
                                self.cell(self.get_string_width(part), 5, part, new_x=XPos.RIGHT)
                                self.set_font(FONT_FAMILY, '', 10)
                            else:
                                self.cell(self.get_string_width(part), 5, part, new_x=XPos.RIGHT)
                        self.ln()
                    else:
                        self.multi_cell(170, 5, text)
                
                # Handle bold text in regular lines
                elif '**' in line:
                    self.set_x(15)
                    parts = line.split('**')
                    for i, part in enumerate(parts):
                        if i % 2 == 1:  # Odd indices are bold
                            self.set_font(FONT_FAMILY, 'B', 10)
                            self.cell(self.get_string_width(part), 5, part, new_x=XPos.RIGHT)
                            self.set_font(FONT_FAMILY, '', 10)
                        else:
                            self.cell(self.get_string_width(part), 5, part, new_x=XPos.RIGHT)
                    self.ln()
                
                # Handle numbered lists
                elif line.startswith(('1. ', '2. ', '3. ', '4. ', '5. ')):
                    self.set_x(15)
                    number = line[:2]
                    text = line[2:].strip()
                    self.cell(10, 5, number)
                    self.set_x(25)
                    self.multi_cell(165, 5, text)
                
                # Regular text
                else:
                    self.set_x(15)
                    self.multi_cell(180, 5, line)
            
            self.ln(4)  # Add space between sections
    def draw_table(self, headers, data, column_widths, align='L'):
        if not data:
            self.set_font(FONT_FAMILY, '', 10)
            self.cell(0, 10, "No data available for this table.", 0, 1, 'L')
            return
        
        # Check if we need a new page for the table
        if self.get_y() + (len(data) * 8) + 20 > 270:
            self.add_page()
            
        self.set_font(FONT_FAMILY, 'B', 10)
        self.set_fill_color(*PRIMARY_COLOR)
        self.set_text_color(255, 255, 255)
        
        # Ensure table doesn't exceed page width (190mm usable width)
        total_width = sum(column_widths)
        if total_width > 190:
            # Scale down column widths proportionally
            scale_factor = 190 / total_width
            column_widths = [int(w * scale_factor) for w in column_widths]
        
        for i, header in enumerate(headers):
            self.cell(column_widths[i], 10, header, border=1, fill=True, align='C')
        self.ln()
        
        self.set_font(FONT_FAMILY, '', 9)
        self.set_text_color(*TEXT_COLOR)
        fill = False
        
        for row in data:
            if self.get_y() + 15 > 270:  # Check if we need a new page
                self.add_page()
            
            self.set_fill_color(*BG_COLOR_LIGHT if fill else (255, 255, 255))
            y_before = self.get_y()
            
            # Draw the cells
            for i, item in enumerate(row):
                if i < len(column_widths):
                    # Ensure text fits within cell width
                    text = str(item)
                    if len(text) > 30:  # Truncate very long text
                        text = text[:27] + "..."
                    self.cell(column_widths[i], 8, text, border=1, fill=True, align=align)
                    
            self.ln()
            fill = not fill
        self.ln(5)

    def draw_key_insights_table(self, data):
        self.chapter_title("Key Financial Insights", level=2)
        
        # Check if we need a new page
        if self.get_y() + (len(data) * 8) + 20 > 270:
            self.add_page()
            
        self.set_font(FONT_FAMILY, 'B', 10)
        self.set_fill_color(*PRIMARY_COLOR)
        self.set_text_color(255, 255, 255)
        self.cell(70, 10, "Metric", border=1, fill=True, align='C')
        self.cell(110, 10, "Value", border=1, fill=True, align='C')
        self.ln()
        
        self.set_font(FONT_FAMILY, '', 9)
        self.set_text_color(*TEXT_COLOR)
        fill = False
        
        for key, value in data.items():
            if self.get_y() + 10 > 270:  # Check if we need a new page
                self.add_page()
                
            self.set_fill_color(*BG_COLOR_LIGHT if fill else (255, 255, 255))
            self.cell(70, 8, key, border=1, fill=True, align='L')
            self.cell(110, 8, str(value), border=1, fill=True, align='L')
            self.ln()
            fill = not fill
        self.ln(5)

    def draw_chart_box(self, title, image_buffer):
        # Check if we have enough space for title + chart (about 100mm)
        if self.get_y() + 100 > 270:
            self.add_page()
            
        self.set_font(FONT_FAMILY, 'B', 12)
        self.set_text_color(*PRIMARY_COLOR)
        self.set_draw_color(200, 200, 200)
        
        # Draw title
        self.cell(0, 10, title, border=0, ln=1, align='C')
        self.ln(5)
        
        # Draw chart with proper centering
        y_before = self.get_y()
        self.image(image_buffer, w=170, x=20)  # Reduced width and centered
        
        # Draw border around the chart area
        chart_height = self.get_y() - y_before
        self.rect(15, y_before - 15, 180, chart_height + 20)
        self.ln(10)

class ReportService:
    def __init__(self, api_base_url, auth_token):
        self.api_base_url = api_base_url
        self.headers = {'Authorization': f'Bearer {auth_token}'}
        self.stats_data = None
        self.all_resources_data = []
        self.image_files = []
        self.groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.pdf = PDF()
        setup_fonts(self.pdf)

    def fetch_data(self):
        try:
            stats_response = requests.get(f"{self.api_base_url}/api/resources/stats", headers=self.headers)
            stats_response.raise_for_status()
            self.stats_data = stats_response.json().get('data', {})
            
            resources_response = requests.get(f"{self.api_base_url}/api/resources?limit=5000", headers=self.headers)
            resources_response.raise_for_status()
            self.all_resources_data = resources_response.json().get('resources', [])
            
            print(f"Fetched {len(self.all_resources_data)} resources")
            print(f"Stats data keys: {list(self.stats_data.keys()) if self.stats_data else 'None'}")
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            raise

    def get_ai_summary(self):
        if not self.stats_data:
            return "### Error\nNo statistics data available for analysis."

        total_resources = self.stats_data.get("total_resources", 0)
        total_cost = self.stats_data.get("total_cost", 0)
        
        prompt = f"""
        Analyze the asset data for M.S. Ramaiah Institute of Technology.
        Total Assets: {total_resources}
        Total Value: {RUPEE_SYMBOL}{total_cost:,.2f}
        
        Structure your response using the exact format below:

        ### Executive Summary
        Provide a brief summary of the total assets and their value.

        ### Operational Distribution
        Comment on asset distribution across departments.

        """
        return self.get_groq_completion(prompt)

    def get_groq_completion(self, content):
        try:
            if not self.groq_client:
                return "### Error\nGroq API client not initialized."
                
            chat_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": content}],
                model="llama3-8b-8192",
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error with Groq API: {e}")
            return "### Error\nAI analysis could not be generated due to an API error."

    def create_visualizations(self):
        if not self.stats_data:
            print("No stats data available for visualizations")
            return
            
        title_color = tuple(c/255 for c in PRIMARY_COLOR)
        
        # Department count chart
        dept_stats = self.stats_data.get('department_stats', [])
        if dept_stats:
            dept_stats = sorted(dept_stats, key=lambda x: x.get('count', 0), reverse=True)[:10]
            departments = [textwrap.fill(d.get('_id', 'Unknown'), 15) for d in dept_stats]
            counts = [d.get('count', 0) for d in dept_stats]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(departments, counts, color=plt.cm.Paired.colors)
            ax.set_ylabel('Number of Assets')
            ax.set_title('Top 10 Departments by Asset Count', fontsize=14, fontweight='bold', color=title_color)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            self.save_chart_to_buffer(fig)
        
        # Department cost chart
        dept_cost_stats = self.stats_data.get('department_cost_stats', [])
        if dept_cost_stats:
            dept_cost_stats = sorted(dept_cost_stats, key=lambda x: x.get('total_cost', 0), reverse=True)[:10]
            departments = [textwrap.fill(d.get('_id', 'Unknown'), 20) for d in dept_cost_stats]
            costs = [d.get('total_cost', 0) for d in dept_cost_stats]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(departments, costs, color=plt.cm.Set3.colors)
            ax.set_xlabel(f'Total Asset Value ({RUPEE_SYMBOL})')
            ax.set_title('Top 10 Departments by Asset Value', fontsize=14, fontweight='bold', color=title_color)
            ax.invert_yaxis()
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{RUPEE_SYMBOL}{x:,.0f}'))
            plt.tight_layout()
            self.save_chart_to_buffer(fig)
    def create_parent_department_visualization(self):
        parent_department_counts = defaultdict(int)

        for asset in self.all_resources_data:
            parent_dept = asset.get('parent_department') or 'Unknown'
            parent_department_counts[parent_dept] += 1

        if not parent_department_counts:
            return

        # Sort and take top 10
        sorted_parents = sorted(parent_department_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        labels, values = zip(*sorted_parents)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(labels, values, color=plt.cm.Accent.colors)
        ax.set_ylabel('Number of Resources')
        ax.set_title('Top 10 Parent Departments by Resource Count', fontsize=14, fontweight='bold', color=(0.02, 0.16, 0.36))
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        self.save_chart_to_buffer(fig)

    def save_chart_to_buffer(self, fig):
        try:
            img_buf = io.BytesIO()
            fig.tight_layout(pad=1.5)
            plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
            img_buf.seek(0)
            self.image_files.append(img_buf)
            plt.close(fig)
        except Exception as e:
            print(f"Error saving chart: {e}")
            plt.close(fig)

    def generate_comprehensive_report(self):
        try:
            self.fetch_data()
            ai_summary = self.get_ai_summary()
            self.create_visualizations()
            self.create_parent_department_visualization()  # <-- add this line

            pdf = self.pdf
            pdf.cover_page()

            # Page 2: AI Summary and Key Insights
            pdf.add_page()
            
            # Write AI Summary (modified to remove recommendations)
            if "### Actionable Recommendations" in ai_summary:
                ai_summary = ai_summary.split("### Actionable Recommendations")[0]
            pdf.write_ai_summary(ai_summary)
            pdf.add_page()

            # Prepare data for the Key Insights table
            cost_stats = self.stats_data.get('cost_statistics', {})
            
            # Department analysis
            dept_cost_stats = self.stats_data.get('department_cost_stats', [])
            top_dept = max(dept_cost_stats, key=lambda x: x.get('total_cost', 0)) if dept_cost_stats else {'_id': 'N/A', 'total_cost': 0}
            
            # Location analysis
            location_financials = defaultdict(lambda: {'cost': 0, 'count': 0})
            for asset in self.all_resources_data:
                loc = asset.get('location') or 'Unspecified'
                location_financials[loc]['cost'] += asset.get('cost', 0)
                location_financials[loc]['count'] += 1
            
            top_loc_item = max(location_financials.items(), key=lambda item: item[1]['cost']) if location_financials else ('N/A', {'cost': 0})
            
            insights_data = {
                "Total Asset Value": f"{RUPEE_SYMBOL}{self.stats_data.get('total_cost', 0):,.2f}",
                "Total Asset Count": f"{self.stats_data.get('total_resources', 0):,}",
                "Average Asset Value": f"{RUPEE_SYMBOL}{cost_stats.get('average_cost', 0):,.2f}",
                "Highest Value Asset": f"{RUPEE_SYMBOL}{cost_stats.get('max_cost', 0):,.2f}",
                "Lowest Value Asset": f"{RUPEE_SYMBOL}{cost_stats.get('min_cost', 0):,.2f}",
                "Department with Highest Value": f"{top_dept.get('_id', 'N/A')} ({RUPEE_SYMBOL}{top_dept.get('total_cost', 0):,.2f})",
                "Location with Highest Value": f"{top_loc_item[0]} ({RUPEE_SYMBOL}{top_loc_item[1]['cost']:,.2f})"
            }
            
            # Add Key Insights right after AI Summary
            pdf.draw_key_insights_table(insights_data)

            # Page 3: Visualizations
            if self.image_files:
                pdf.add_page()
                pdf.chapter_title("Asset Distribution Visualizations")
                chart_titles = ["Department Analysis: Asset Count", "Department Analysis: Asset Value"]
                
                for i, img_buffer in enumerate(self.image_files):
                    if i < len(chart_titles):
                        pdf.draw_chart_box(chart_titles[i], img_buffer)
                        if i < len(self.image_files) - 1:
                            pdf.ln(10)

            # Page 4: Detailed Tabular Breakdowns
            pdf.add_page()
            pdf.chapter_title("Detailed Financial Breakdowns")

            # Department Financial Summary Table
            dept_cost_stats = self.stats_data.get('department_cost_stats', [])
            if dept_cost_stats:
                pdf.chapter_title("Departmental Financial Summary", level=2)
                dept_analysis_data = []
                dept_counts = {d.get('_id', 'Unknown'): d.get('count', 0) for d in self.stats_data.get('department_stats', [])}
                
                for dept in sorted(dept_cost_stats, key=lambda x: x.get('total_cost', 0), reverse=True):
                    dept_id = dept.get('_id', 'Unknown')
                    count = dept_counts.get(dept_id, 0)
                    total_cost = dept.get('total_cost', 0)
                    avg_cost = total_cost / count if count > 0 else 0
                    
                    # Truncate long department names
                    display_name = dept_id
                    if len(display_name) > 30:
                        display_name = display_name[:27] + "..."
                    
                    dept_analysis_data.append([
                        display_name,
                        f"{count:,}",
                        f"{RUPEE_SYMBOL}{total_cost:,.0f}",
                        f"{RUPEE_SYMBOL}{avg_cost:,.0f}"
                    ])
                pdf.draw_table(["Department", "Count", "Total Value", "Average Value"], dept_analysis_data, [60, 30, 50, 50])

            # Location Financial Summary Table
            if location_financials:
                pdf.chapter_title("Location Financial Summary", level=2)
                location_data = []
                for loc, data in sorted(location_financials.items(), key=lambda item: item[1]['cost'], reverse=True):
                    count = data['count']
                    cost = data['cost']
                    avg_cost = cost / count if count > 0 else 0
                    
                    # Truncate long location names
                    display_loc = loc
                    if len(display_loc) > 30:
                        display_loc = display_loc[:27] + "..."
                    
                    location_data.append([
                        display_loc,
                        f"{count:,}",
                        f"{RUPEE_SYMBOL}{cost:,.0f}",
                        f"{RUPEE_SYMBOL}{avg_cost:,.0f}"
                    ])
                pdf.draw_table(["Location (Section/Lab)", "Count", "Total Value", "Average Value"], location_data, [60, 30, 50, 50])

            # Page 5: High-Value Assets Register
            if self.all_resources_data:
                pdf.add_page()
                pdf.chapter_title("High-Value Asset Register")
                pdf.chapter_title("Top 20 Most Valuable Assets", level=2)
                top_assets = sorted(self.all_resources_data, key=lambda x: x.get('cost', 0), reverse=True)[:20]
                high_value_data = []
                for asset in top_assets:
                    # Truncate long descriptions
                    desc = asset.get('description', 'N/A')
                    if len(desc) > 35:
                        desc = desc[:32] + "..."
                    
                    dept = asset.get('department', 'N/A')
                    if len(dept) > 25:
                        dept = dept[:22] + "..."
                        
                    loc = asset.get('location', 'N/A')
                    if len(loc) > 25:
                        loc = loc[:22] + "..."
                    
                    high_value_data.append([
                        desc,
                        dept,
                        loc,
                        f"{RUPEE_SYMBOL}{asset.get('cost', 0):,.0f}"
                    ])
                pdf.draw_table(["Description", "Department", "Location", "Cost"], high_value_data, [60, 40, 40, 40])

            self.cleanup()
            pdf_buffer = io.BytesIO(pdf.output())
            pdf_buffer.seek(0)
            return pdf_buffer
            
        except Exception as e:
            print(f"Report generation error: {e}")
            self.cleanup()
            raise
    def cleanup(self):
        for image_buffer in self.image_files:
            image_buffer.close()
        self.image_files = []