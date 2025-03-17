import zipfile
import os
import json

def convert_pbix_to_json(pbix_file_path, output_json_path):
    # Step 1: Rename the .pbix file to .zip and extract it
    zip_file_path = pbix_file_path.replace(".pbix", ".zip")
    os.rename(pbix_file_path, zip_file_path)

    # Step 2: Extract the .zip file
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        extract_path = zip_file_path.replace(".zip", "_extracted")
        zip_ref.extractall(extract_path)

    # Step 3: Look for the DataModelSchema file
    data_model_schema_path = None
    for root, dirs, files in os.walk(extract_path):
        for file in files:
            if file == "DataModelSchema":
                data_model_schema_path = os.path.join(root, file)
                break

    if data_model_schema_path is None:
        raise FileNotFoundError("DataModelSchema not found in the extracted .pbix file")

    # Step 4: Try reading the file content with different encodings
    encodings_to_try = ['utf-16', 'utf-8', 'latin-1']  # Add other encodings if necessary
    data_model_content = None
    for encoding in encodings_to_try:
        try:
            with open(data_model_schema_path, 'r', encoding=encoding) as schema_file:
                data_model_content = schema_file.read()
            print(f"Successfully read DataModelSchema with {encoding} encoding")
            break
        except UnicodeError:
            print(f"Failed to read with {encoding}, trying the next encoding...")

    if data_model_content is None:
        raise UnicodeError("Failed to read DataModelSchema with all tried encodings")

    # Step 5: Optionally, save the DataModelSchema content as JSON for custom modifications
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(json.loads(data_model_content), json_file, indent=4)

    # Step 6: Clean up the intermediate .zip file if needed
    os.remove(zip_file_path)

    print(f"Conversion complete! JSON saved at: {output_json_path}")

# Example usage
pbix_file_path = "server data new data(172.16.16.23,aiml).pbix"  # Replace with the actual .pbix file path
output_json_path = "output_template.json"  # Replace with the desired output JSON path

convert_pbix_to_json(pbix_file_path, output_json_path)
