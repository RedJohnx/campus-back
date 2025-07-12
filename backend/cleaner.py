import pandas as pd

# Read the Excel file, specifying the sheet and disabling header interpretation
df = pd.read_excel('Systems in the Department 15-02-2024.xlsx', sheet_name='Auto & Process', header=None)

# Initialize variables to track state
current_department = None
last_description = None
last_location = None
data_list = []
sl_no_counter = 1  # Start the SL No counter at 1

# Iterate through each row of the DataFrame
for index, row in df.iterrows():
    # Skip completely empty rows
    if pd.isna(row).all():
        continue
    # Identify department name (row with only first cell non-empty)
    elif not pd.isna(row[0]) and pd.isna(row[1:]).all():
        current_department = row[0]
    # Skip header row of tables
    elif str(row[0]).strip() == 'Sl. No':
        continue
    # Process data rows (first cell is SL No and not NaN)
    elif not pd.isna(row[0]):
        # Extract fields, handling potential NaN values
        description = row[1] if not pd.isna(row[1]) else last_description
        service_tag = row[2] if not pd.isna(row[2]) else ''
        identification_no = row[3] if not pd.isna(row[3]) else ''
        # Format procurement_date to only include date (YYYY-MM-DD)
        if not pd.isna(row[4]):
            if isinstance(row[4], pd.Timestamp):
                procurement_date = row[4].strftime('%Y-%m-%d')
            else:
                # Try to parse string to date if it contains time
                try:
                    procurement_date = str(pd.to_datetime(row[4])).split(' ')[0]
                except Exception:
                    procurement_date = str(row[4])
        else:
            procurement_date = ''
        cost = row[5] if not pd.isna(row[5]) else ''
        location = row[6] if not pd.isna(row[6]) else last_location
        department = current_department

        # Update last_description and last_location for carry-forward
        if not pd.isna(row[1]):
            last_description = row[1]
        if not pd.isna(row[6]):
            last_location = row[6]

        # Append the cleaned row to data_list with the new SL No
        data_list.append({
            'SL No': sl_no_counter,  # Use the counter instead of the original SL No
            'Description': description,
            'Service Tag': service_tag,
            'Identification Number': identification_no,
            'Procurement Date': procurement_date,
            'Cost': cost,
            'Location': location,
            'Department': department
        })

        # Increment the SL No counter
        sl_no_counter += 1
    # Skip cumulative count rows (first cell NaN, last cell has a number)
    elif pd.isna(row[0]) and not pd.isna(row[6]):
        continue

# Create a new DataFrame from the cleaned data
cleaned_df = pd.DataFrame(data_list)

# Write the cleaned DataFrame to a new Excel file
cleaned_df.to_excel('cleaned_systems.xlsx', index=False)

print("Processing complete. The cleaned data has been saved to 'cleaned_systems.xlsx'.")