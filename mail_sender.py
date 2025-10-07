import os
import logging
import smtplib
import zipfile
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from config.path_declarations import *
from config.experiment_settings import *

logger = logging.getLogger(__name__)

def enviar_archivos_por_gmail(seed, config, target_file_name, sobol):
    """Sends experimental data and results via email as a zip attachment.

    Compiles experiment results, configuration details, and log files into a zip archive
    and sends them to specified recipients via Gmail. Handles all aspects of email creation
    including authentication, message formatting, file attachment, and error handling.

    Args:
        seed (int): The random seed used for the experiment
        config (object): Configuration object containing:
            - DATA_UTC: Timestamp for experiment identification
            - FIG_PATH: Directory containing result files to send
            - LOG_FILE: Path to the experiment log file
        target_file_name (str): Name of the target file used in the experiment
        sobol (int): Number of Sobol trials performed

    Returns:
        None: Sends email but doesn't return a value

    Raises:
        FileNotFoundError: If specified directories/files don't exist
        smtplib.SMTPException: For email sending failures
        RuntimeError: For zip file creation problems

    Examples:
        >>> send_experiment_data_via_gmail(42, config, "target1", 100)
        # Sends email with experiment data attached

    Note:
        - Uses Gmail SMTP server on port 587 with TLS
        - Requires app-specific password for authentication
        - Creates temporary zip file that's automatically deleted
        - Includes comprehensive error logging
        - Supports multiple recipients
        - Email contains full experiment configuration details
    """
    # Email configuration
    remitente = "utike112@gmail.com"
    password = "wzyu zqie oifa kajl"  # Application password
    destinatarios = ["utike112@gmail.com", "alopez419@ikasle.ehu.eus", "grzelczak.marek@gmail.com"]#, "grzelczak.marek@gmail.com"]  # List of recipients 
    asunto = f"Datas of Experiment_{config.DATA_UTC}"
    mensaje = "This experiment was conducted with the following configuration:"
    
    if REAL_EXP:
        if SPECTRAL_MATCHING:
            conf = f'REAL_EXP: {REAL_EXP}, SPECTRAL_MATCHING: {SPECTRAL_MATCHING}, MINIMIZE_ERROR: {MINIMIZE_ERROR}'
        elif MAXIMIZE_TEMP:
            conf = f'REAL_EXP: {REAL_EXP}, MAXIMIZE_TEMP: {MAXIMIZE_TEMP}'
    elif TESTER_EXP:
        conf = f"TEST_EXP: {TESTER_EXP}, PARAM_MATCHING: {PARAM_MATCHING}, MINIMIZE_ERROR: {MINIMIZE_ERROR}"

    seed_obj = f'The experiment seed is {seed} and the objective was {target_file_name}'
    exp_set = f'With {sobol} SOBOL trials and {NUM_TRIALS_FB} Fully Bayesian trials'
    full_msg = f'{mensaje}\n{conf}\n{exp_set}\n{seed_obj}'

    # Folder with the files to send
    carpeta_archivos = config.FIG_PATH
    file_logs = config.LOG_FILE
    
    # Create the message
    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = ", ".join(destinatarios)
    msg['Subject'] = asunto
    msg.attach(MIMEText(full_msg, 'plain'))
    
    # Create a temporary zip file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        zip_filename = tmp_zip.name
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add files from the folder
            archivos = [f for f in os.listdir(carpeta_archivos) if os.path.isfile(os.path.join(carpeta_archivos, f))]
            
            if not archivos:
                logger.warning("There are no files in the specified folder")
                return
            
            for archivo in archivos:
                ruta_completa = os.path.join(carpeta_archivos, archivo)
                try:
                    zipf.write(ruta_completa, arcname=archivo)
                    logger.info(f"File added to zip: {archivo}")
                except Exception as e:
                    logger.error(f"Error adding {archivo} to zip: {str(e)}")
            
            # Add log file if it exists
            if os.path.isfile(file_logs):
                try:
                    zipf.write(file_logs, arcname=os.path.basename(file_logs))
                    logger.info(f"Log file added to zip: {file_logs}")
                except Exception as e:
                    logger.error(f"Error adding log file {file_logs} to zip: {str(e)}")
            else:
                logger.warning(f"Log file not found: {file_logs}")
    
    # Attach the zip file
    try:
        with open(zip_filename, 'rb') as zip_file:
            part = MIMEBase('application', 'zip')
            part.set_payload(zip_file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename=Experiment_{config.DATA_UTC}.zip')
            msg.attach(part)
    except Exception as e:
        logger.error(f"Error attaching zip file: {str(e)}")
    finally:
        # Clean up the temporary zip file
        os.unlink(zip_filename)
    
    # Send mail
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.sendmail(remitente, destinatarios, msg.as_string())
        server.quit()
        logger.info(f"Email successfully sent to: {', '.join(destinatarios)}")
    except Exception as e:
        logger.error(f"Error sending the email: {str(e)}")

def send_experiment_completion_notification(config):
    """Sends an email notification with attached results when all experiments complete.

    Compiles all experimental data files into a zip archive and sends them via email
    to notify recipients that the experiment batch has finished. Includes clear next steps
    in the message body and handles all email creation, authentication, and file attachment.

    Args:
        config (object): Configuration object containing:
            - GLOBAL_DATAS: Directory containing result files to send
            - DATA_UTC: Timestamp for experiment identification

    Returns:
        None: Sends email but doesn't return a value

    Raises:
        FileNotFoundError: If specified directory doesn't exist
        smtplib.SMTPException: For email sending failures
        RuntimeError: For zip file creation problems

    Examples:
        >>> send_experiment_completion_notification(config)
        # Sends completion email with data attachments

    Note:
        - Uses Gmail SMTP with TLS encryption
        - Requires app-specific password for authentication
        - Creates temporary zip file that's automatically deleted
        - Includes comprehensive error logging
        - Supports multiple recipients
        - Provides clear next steps in message body
    """
    # Email configuration
    sender = "utike112@gmail.com"
    password = "wzyu zqie oifa kajl"
    recipients = ["utike112@gmail.com", "alopez419@ikasle.ehu.eus", "grzelczak.marek@gmail.com"]#, "grzelczak.marek@gmail.com"]
    
    # Construct message
    subject = "Experiment Batch Completed"
    message = """All experiments have finished successfully!

Next Steps:
1. Review the collected data
2. Adjust laboratory parameters as needed
3. Prepare for next experiment batch

I'll be waiting in the lab!"""

    # Folder with the files to send
    carpeta_archivos = config.GLOBAL_DATAS
    
    # Create email
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    # Create a temporary zip file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        zip_filename = tmp_zip.name
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add files from the folder
            archivos = [f for f in os.listdir(carpeta_archivos) if os.path.isfile(os.path.join(carpeta_archivos, f))]
            
            if not archivos:
                logger.warning("There are no files in the specified folder")
                return
            
            for archivo in archivos:
                ruta_completa = os.path.join(carpeta_archivos, archivo)
                try:
                    zipf.write(ruta_completa, arcname=archivo)
                    logger.info(f"File added to zip: {archivo}")
                except Exception as e:
                    logger.error(f"Error adding {archivo} to zip: {str(e)}")
    
    # Attach the zip file
    try:
        with open(zip_filename, 'rb') as zip_file:
            part = MIMEBase('application', 'zip')
            part.set_payload(zip_file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename=Experiment_{config.DATA_UTC}.zip')
            msg.attach(part)
    except Exception as e:
        logger.error(f"Error attaching zip file: {str(e)}")
    finally:
        # Clean up the temporary zip file
        os.unlink(zip_filename)
    
    # Send mail
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()
        logger.info(f"Email successfully sent to: {', '.join(recipients)}")
    except Exception as e:
        logger.error(f"Error sending the email: {str(e)}")

def send_error_notification(error_message=None):
    """Sends an email notification when an experiment encounters an error.

    Constructs and sends an error notification email to specified recipients when
    an experiment fails. Includes detailed error information if provided, and
    handles all aspects of email creation and transmission.

    Args:
        error_message (str, optional): Detailed error message to include in notification.
            If None, a generic error message will be sent. Defaults to None.

    Returns:
        None: The function sends an email but does not return any value.

    Raises:
        smtplib.SMTPException: If there is an error during email transmission.
        RuntimeError: If the email cannot be constructed or sent.

    Examples:
        >>> send_error_notification("Temperature exceeded safe limits")
        # Sends error email with the specified message

        >>> send_error_notification()
        # Sends generic error notification

    Note:
        - Uses Gmail's SMTP server with TLS encryption
        - Requires application-specific password for authentication
        - Sends to predefined recipient list
        - Includes timestamp in the email subject
        - Logs both successful and failed attempts
        - Re-raises exceptions after logging them
    """
    try:
        # Email configuration
        sender = "utike112@gmail.com"
        password = "wzyu zqie oifa kajl"
        recipients = ["utike112@gmail.com", "alopez419@ikasle.ehu.eus", "grzelczak.marek@gmail.com"] #, "grzelczak.marek@gmail.com"
        
        # Construct message with timestamp
        subject = "Experiment Batch not completed"
        base_message = """Unexpected error ocurred during the experiment"""
        detailed_message = f"{base_message}\n\nError details:\n{str(error_message)}" if error_message else base_message
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(detailed_message, 'plain'))
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())
        
        logger.info("Experiment completion notification sent successfully")
        
    except Exception as e:
        logger.error(f"Failed to send completion notification: {str(e)}")
        raise


