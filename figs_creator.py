import os
import re
import logging
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from config.path_declarations import *
from config.experiment_settings import *

logger = logging.getLogger(__name__)

def create_multiple_plots_pdf(config):
    """Generates a PDF document containing multiple plot images arranged in a grid layout.

    Creates a multi-page PDF with plots arranged in a 3x7 grid (21 plots per page) from PNG
    files in a specified directory. Maintains proper aspect ratio and includes automatic
    pagination and consistent margins.

    Args:
        config (object): Configuration object containing:
            - FIG_PATH: Output path for PDF file
            - SPECTRA_PLOTS: Directory containing PNG plot files

    Returns:
        None: Creates a PDF file at the specified location

    Raises:
        FileNotFoundError: If SPECTRA_PLOTS directory doesn't exist
        ValueError: If no PNG files found in directory
        PermissionError: If unable to write to output PDF

    Examples:
        >>> create_multiple_plots_pdf(config)
        # Generates 'compare_plots.pdf' in FIG_PATH directory

    Note:
        - Uses A4 page size (210x297mm) with 15mm margins
        - Each plot is 60x35mm (width x height)
        - Arranges plots in 3 columns and 7 rows per page
        - Sorts files numerically by embedded numbers in filenames
        - Preserves original image aspect ratios
        - Logs successful PDF generation
    """
    # Page dimensions and layout constants
    A4_WIDTH, A4_HEIGHT = A4                        # Standard A4 dimensions (210x297mm)
    PLOTS_PER_PAGE = 21                             # 3 columns x 7 rows
    PLOT_WIDTH = 60 * mm                            # Individual plot width
    PLOT_HEIGHT = 35 * mm                           # Individual plot height
    MARGIN_X = (A4_WIDTH - 3 * PLOT_WIDTH) / 2      # Horizontal centering margin
    MARGIN_Y = 15 * mm                              # Top/bottom margin

    def extract_number(filename):
        """Extracts numerical value from filename for sorting.
        
        Args:
            filename (str): The filename to process
            
        Returns:
            int: Extracted number or 0 if no number found
        """
        match = re.search(r'\d+', filename)
        return int(match.group()) if match else 0

    def create_pdf(folder_path, output_pdf_name):
        """Creates PDF document from PNG files in specified folder.
        
        Args:
            folder_path (str): Directory containing PNG files
            output_pdf_name (str): Path for output PDF file
        """
        # Get and sort PNG files by embedded numbers
        png_files = sorted(
            [f for f in os.listdir(folder_path) if f.endswith('.png')],
            key=extract_number
        )
        
        # Initialize PDF canvas
        c = canvas.Canvas(output_pdf_name, pagesize=A4)
        
        for i, png_file in enumerate(png_files):
            # Create new page after every 21 plots
            if i % PLOTS_PER_PAGE == 0 and i > 0:
                c.showPage()
            
            # Calculate grid position
            row = (i % PLOTS_PER_PAGE) // 3 # 0-6 row index
            col = (i % PLOTS_PER_PAGE) % 3  # 0-2 column index
            
            # Calculate plot position
            x = MARGIN_X + col * PLOT_WIDTH
            y = A4_HEIGHT - MARGIN_Y - (row + 1) * PLOT_HEIGHT

            # Draw image while preserving aspect ratio
            img_path = os.path.join(folder_path, png_file)
            c.drawImage(img_path, x, y, PLOT_WIDTH, PLOT_HEIGHT, preserveAspectRatio=True)
        
        c.save()
        logger.info(f"PDF generated: '{output_pdf_name}'")

    # Generate comparison figure PDFt
    compare_fig=os.path.join(config.FIG_PATH, 'compare_plots.pdf')
    create_pdf(config.SPECTRA_PLOTS, compare_fig)

def create_combined_report_pdf(config):
    """Generates a comprehensive PDF report combining multiple experimental visualizations.

    Creates a multi-section PDF report containing:
    1. Individual plots (loss and temperature stability)
    2. Combined loss vs temperature stability plot
    3. Detailed temperature profile plot
    All sections are properly formatted on an A4 page with consistent margins.

    Args:
        config (object): Configuration object containing:
            - FIG_PATH: Output directory for PDF
            - TEMP_PLOTS: Directory for temperature plots
            - LOSS_EXP: Directory for loss experiment data
            - TEMP_FILE: Directory for temperature data files
            - DATA_UTC: Timestamp for file naming

    Returns:
        None: Generates a PDF file at the specified location

    Raises:
        FileNotFoundError: If required input files are missing
        ValueError: If data files are malformed
        PermissionError: If unable to write output PDF

    Examples:
        >>> create_combined_report_pdf(config)
        # Generates 'general_fig.pdf' in FIG_PATH directory

    Note:
        - Uses A4 page size (210x297mm) with 15mm side margins
        - Maintains consistent spacing between sections (25mm)
        - Automatically generates combined loss/temperature plot
        - Cleans up temporary files after PDF generation
        - Preserves original image aspect ratios
        - Logs missing files as errors
    """
    # Page layout constants
    A4_WIDTH, A4_HEIGHT = A4    # Standard A4 dimensions in points (595x842)
    MARGIN_X = 15 * mm          # Left/right margin
    TOP_MARGIN = 20 * mm        # Top margin
    SECTION_GAP = 25 * mm       # Vertical space between sections
    PLOT_WIDTH = 80 * mm        # Width for individual plots
    COMBINED_WIDTH = 160 * mm   # Width for combined plot
    TEMP_WIDTH = 160 * mm       # Width for temperature plot

    # Directory paths from config
    CARPETA_PLOTS = config.TEMP_PLOTS  # Directory for plot images
    CARPETA_LOSS = config.LOSS_EXP  # Directory for loss data
    CARPETA_TEMP = config.TEMP_FILE  # Directory for temperature data

    def create_pdf(config):
        """Internal function to handle PDF creation."""
        general_fig=os.path.join(config.FIG_PATH, 'general_fig.pdf')
        c = canvas.Canvas(general_fig, pagesize=A4)
        y_position = A4_HEIGHT - TOP_MARGIN # Current vertical position

        # --- Section 1: Individual plots ---
        loss_img = os.path.join(CARPETA_PLOTS, "loss_plot.png")
        temp_stab_img = os.path.join(CARPETA_PLOTS, f"Plot_temp_stab_{config.DATA_UTC}.png")
        
        if all(os.path.exists(img) for img in [loss_img, temp_stab_img]):
            c.drawImage(loss_img, MARGIN_X, y_position - 60*mm, 
                       width=PLOT_WIDTH, height=60*mm, preserveAspectRatio=True)
            c.drawImage(temp_stab_img, MARGIN_X + PLOT_WIDTH + 10*mm, y_position - 60*mm,
                       width=PLOT_WIDTH, height=60*mm, preserveAspectRatio=True)
            y_position -= 70*mm
        else:
            logger.error("Missing images in Section 1!")

        # --- Section 2: Combined plot ---
        loss_file = os.path.join(CARPETA_LOSS, f"Loss_Experiment_{config.DATA_UTC}.txt")
        temp_file = os.path.join(CARPETA_TEMP, "Stabilized_Temps.txt")
        
        if all(os.path.exists(f) for f in [loss_file, temp_file]):
            def load_data(file_path, is_loss=True):
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                trials, values = [], []
                for line in lines:
                    parts = line.strip().split()
                    trials.append(int(parts[3] if is_loss else parts[4]))
                    values.append(float(parts[-1]))
                return trials, values
            
            trials_loss, losses = load_data(loss_file)
            trials_temp, temps = load_data(temp_file, False)

            plt.style.use('default')
            fig, ax1 = plt.subplots(figsize=(8, 4))
            
            ax1.grid(True, linestyle='--', alpha=0.6)
            
            ax1.plot(trials_loss, losses, 'b-', label='Loss', linewidth=2)
            ax1.set_xlabel("Trial Number", fontsize=10, color='black')
            ax1.set_ylabel("Loss Value", fontsize=10, color='black')
            ax1.tick_params(axis='y', colors='black')
            
            ax2 = ax1.twinx()
            ax2.plot(trials_temp, temps, 'r--', label='Temp Stability', linewidth=2)
            ax2.set_ylabel("Temperature [°C]", fontsize=10, color='black')
            ax2.tick_params(axis='y', colors='black')
            
            lines = ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
            plt.legend(lines, [l.get_label() for l in lines], 
                     loc='upper center', bbox_to_anchor=(0.5, 1.18),
                     ncol=2, fontsize=9, framealpha=1)

            temp_path = "temp_combined.png"
            plt.savefig(temp_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            c.drawImage(temp_path, MARGIN_X, y_position - 80*mm,
                       width=COMBINED_WIDTH, height=80*mm, preserveAspectRatio=True)
            os.remove(temp_path)
            y_position -= 90*mm
        else:
            logger.error("Missing data files!")

        # --- Section 3: Temperature plot ---
        temp_img = os.path.join(CARPETA_PLOTS, f"Plot_temp_{config.DATA_UTC}.png")
        if os.path.exists(temp_img):
            c.drawImage(temp_img, MARGIN_X, y_position - 90*mm,
                       width=TEMP_WIDTH, height=90*mm, preserveAspectRatio=True)
        
        c.save()
        print(f"PDF generated: {general_fig}")

    create_pdf(config)

# Run both scripts
def create_figs(config):
    create_multiple_plots_pdf(config)
    if MAXIMIZE_TEMP:
        create_combined_report_pdf(config)