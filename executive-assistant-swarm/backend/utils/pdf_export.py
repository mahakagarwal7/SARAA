import os
from markdown import markdown
from fpdf import FPDF, HTMLMixin

class PDF(FPDF, HTMLMixin):
    pass

class PDFExporter:
    @staticmethod
    def export_markdown_to_pdf(markdown_text: str, output_filename: str) -> str:
        """
        Converts Markdown text to HTML and then generates a PDF file.
        Returns the absolute path to the generated PDF.
        """
        # Ensure outputs directory exists
        outputs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        
        output_path = os.path.join(outputs_dir, output_filename)
        
        # Convert Markdown to HTML
        html_text = markdown(markdown_text)
        
        # Initialize PDF
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Write HTML to PDF
        # We need to wrap it in basic html tags sometimes or directly write it
        try:
            pdf.write_html(html_text)
        except Exception as e:
            print(f"Error writing HTML to PDF: {e}. Falling back to plain text.")
            safe_text = markdown_text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, text=safe_text)
            
        # Save the PDF
        pdf.output(output_path)
        
        return output_path
