import boto3
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime,date
from tkcalendar import DateEntry

def connect_s3(access_key, secret_key, region):
    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )

def list_objects_recursive(s3_client, bucket, prefix=''):
    files = []
    continuation_token = None
    while True:
        params = {'Bucket': bucket, 'Prefix': prefix, 'MaxKeys': 1000}
        if continuation_token:
            params['ContinuationToken'] = continuation_token
        response = s3_client.list_objects_v2(**params)
        files.extend(response.get('Contents', []))
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    return files

def log_to_output(message):
    output_box.insert(tk.END, message + "\n")
    output_box.see(tk.END)

def threaded_copy():
    access_key = entry_access_key.get().strip()
    secret_key = entry_secret_key.get().strip()
    source_bucket = entry_source_bucket.get().strip()
    dest_bucket = entry_dest_bucket.get().strip()

    if not source_bucket or not dest_bucket:
        messagebox.showwarning("Input Error", "Please fill all fields.")
        return

    try:
        s3_source = connect_s3(access_key, secret_key, 'us-east-1')
        s3_dest = connect_s3(access_key, secret_key, 'ap-south-1')

        files = list_objects_recursive(s3_source, source_bucket)
        copied_folders = set()
        failed = []

        for file in files:
            key = file['Key']
            folder = key.split('/')[0]

            if folder not in copied_folders:
                output_box.after(0, log_to_output, f"📂 Copying folder: {folder}")
                copied_folders.add(folder)

            try:
                copy_source = {'Bucket': source_bucket, 'Key': key}
                metadata = {'original-lastmodified': file['LastModified'].replace(tzinfo=None).isoformat()}
                s3_dest.copy(copy_source, dest_bucket, key, ExtraArgs={'Metadata': metadata, 'MetadataDirective': 'REPLACE'})
                output_box.after(0, log_to_output, f"✅ Copied: {key}")
            except Exception as e:
                failed.append((key, str(e)))
                output_box.after(0, log_to_output, f"❌ Failed: {key} - {e}")

        if failed:
            messagebox.showerror("Partial Success", "Some files failed to copy.")
        else:
            messagebox.showinfo("Success", "All files copied successfully!")

    except Exception as e:
        messagebox.showerror("Error", str(e))

def start_copy_thread():
    thread = threading.Thread(target=threaded_copy)
    thread.start()

def threaded_list_files():
    access_key = entry_access_key.get().strip()
    secret_key = entry_secret_key.get().strip()
    source_bucket = entry_source_bucket.get().strip()

    if not source_bucket:
        messagebox.showwarning("Input Error", "Source bucket is required.")
        return

    try:
        s3_client = connect_s3(access_key, secret_key, 'us-east-1')
        files = list_objects_recursive(s3_client, source_bucket)

        start_date = cal_start.get_date()
        end_date = cal_end.get_date()
        today=date.today()

        if start_date>end_date:
            messagebox.showerror("Date Error","End date cannot be before start date.")
            return
        
        if end_date>today:
            messagebox.showerror("Date Error","End date cannot exceed todays date.")
            return

        output_box.after(0, log_to_output, f"🔍 Listing files in {source_bucket} between {start_date} and {end_date}")

        for file in files:
            last_modified = file['LastModified'].replace(tzinfo=None)
            if start_date <= last_modified.date() <= end_date:
                output_box.after(0, log_to_output, f"{file['Key']} | Last Modified: {last_modified}")

        output_box.after(0, log_to_output, f"✅ Done listing files.")

    except Exception as e:
        messagebox.showerror("Error", str(e))

def start_list_thread():
    thread = threading.Thread(target=threaded_list_files)
    thread.start()

def threaded_list_dest_files():
    access_key = entry_access_key.get().strip()
    secret_key = entry_secret_key.get().strip()
    dest_bucket = entry_dest_bucket.get().strip()

    if not dest_bucket:
        messagebox.showwarning("Input Error", "Destination bucket is required.")
        return

    start_date = cal_start.get_date()
    end_date = cal_end.get_date()
    today=date.today()

    if end_date<start_date:
        messagebox.showerror("Date Error","End date cannot be before the start date.")
        return

    if end_date>today:
        messagebox.showerror("Date Error","End date cannot exceed today's date.")
        return

    try:
        s3_client = connect_s3(access_key, secret_key, 'ap-south-1')
        files = list_objects_recursive(s3_client, dest_bucket)

        output_box.after(0, log_to_output, f"🔍 Listing DESTINATION files with metadata date between {start_date} and {end_date}")
# Handles the file listing for a given date range when showing the destination side files. 
        for file in files:
            key = file['Key']
            try:
                head_obj = s3_client.head_object(Bucket=dest_bucket, Key=key)
                meta_timestamp = head_obj['Metadata'].get('original-lastmodified')
                if not meta_timestamp:
                    continue

                last_modified = datetime.fromisoformat(meta_timestamp)
                if start_date <= last_modified.date() <= end_date:
                    output_box.after(0, log_to_output, f"{key} | Metadata Date: {meta_timestamp}")

            except Exception as e:
                output_box.after(0, log_to_output, f"⚠️ Error on {key}: {e}")

        output_box.after(0, log_to_output, f"✅ Done listing destination files.")

    except Exception as e:
        messagebox.showerror("Error", str(e))

def start_list_dest_thread():
    thread = threading.Thread(target=threaded_list_dest_files)
    thread.start()

# GUI setup
window = tk.Tk()
window.title("S3 Bucket Tool with Date Filters")
window.geometry("600x500")

label_access_key = tk.Label(window, text="AWS Access Key:")
entry_access_key = tk.Entry(window, width=60)
label_secret_key = tk.Label(window, text="AWS Secret Key:")
entry_secret_key = tk.Entry(window, width=60, show="*")
label_source_bucket = tk.Label(window, text="Source Bucket Name:")
entry_source_bucket = tk.Entry(window, width=60)
label_dest_bucket = tk.Label(window, text="Destination Bucket Name:")
entry_dest_bucket = tk.Entry(window, width=60)
label_start_date = tk.Label(window, text="Start Date:")
cal_start = DateEntry(window, width=20, background='darkblue', foreground='white', date_pattern='yyyy-mm-dd')
label_end_date = tk.Label(window, text="End Date:")
cal_end = DateEntry(window, width=20, background='darkblue', foreground='white', date_pattern='yyyy-mm-dd')
button_copy = tk.Button(window, text="📁 Copy Files", command=start_copy_thread)
button_list_source = tk.Button(window, text="📄 List Source Files (by date)", command=start_list_thread)
button_list_dest = tk.Button(window, text="📄 List Destination Files (by original date)", command=start_list_dest_thread)
output_box = tk.Text(window, height=20, width=80)

label_access_key.pack()
entry_access_key.pack()
label_secret_key.pack()
entry_secret_key.pack()
label_source_bucket.pack()
entry_source_bucket.pack()
label_dest_bucket.pack()
entry_dest_bucket.pack()
label_start_date.pack()
cal_start.pack()
label_end_date.pack()
cal_end.pack()
button_copy.pack(pady=5) #pady=5
button_list_source.pack(pady=5) #pady=5
button_list_dest.pack(pady=5) #pady=5
output_box.pack()

window.mainloop()