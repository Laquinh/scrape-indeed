import pandas as pd
import datetime
import re

file_name_no_extension = 'ofertas_profesor'
file_name = file_name_no_extension + '.csv'

# Remove duplicate data.
# In theory, it should not exist since we are scraping by date, but for some reason,
# when you go through dozens or hundreds of scraped pages, almost all offers are repeated.
# It's a backend issue and not something we can avoid, but it can be remedied with this workaround
df = pd.read_csv(file_name, encoding='UTF8', sep=',', quotechar='"', on_bad_lines='skip')

# Two offers are considered duplicates if they have the same internal code
no_duplicates = df.drop_duplicates(subset=['Código interno'], keep='first')
no_duplicates.to_csv(file_name_no_extension + '-ND.csv', encoding='UTF8', sep=',', quotechar='"', index=False)

# The salary is usually given in ranges: From 1,000 to 2,000 monthly.
# To make it easier to analyse, it would be ideal for the salary to be a single number, not a range.
# We will create a new column that represents the midpoint value of this range.

# Count the amount of numbers in a string.
def count_numbers_in_string(string):
    pattern = r'\b\d+(?:\.\d+)?\b'
    matches = re.findall(pattern, string)
    return len(matches)

# Extract the fixed salary from the salary range
def extract_fixed_salary(salary):
    # For some reason, some salaries are floats, so we convert them to strings
    salary = str(salary)

    # We remove the dots and replace the comma with a dot
    salary = salary.replace('.', '').replace(',', '.')

    # Calculate the amount of numbers in the string
    count = count_numbers_in_string(salary)

    if count == 0: # If there are no numbers, we return None
        return None
    elif count == 1: # If there is only one number, we return it
        return float(re.findall(r'\d+', salary)[0])
    elif count == 2: # If there are two numbers, we return the midpoint
        lower, upper = map(float, re.findall(r'\d+', salary))
        return (lower + upper) / 2
    else: # If there are more than two numbers, we return an error
        return "ERROR"

no_duplicates['Salario corregido'] = no_duplicates['Salario'].apply(extract_fixed_salary)

# We also created a new column, the periodicity: 10 000 € per month is not the same as 10 000 € per year.
# It is important to note that some salaries are given in languages other than Spanish.
def extract_periodicity(salary):
    salary = str(salary)
    if salary == 'nan' or salary == 'None':
        return None
    elif any(substring in salary for substring in ['an', 'añ', 'year', 'urte']): # "año", "anual", "any", etc.
        return 'año'
    elif any(substring in salary for substring in ['me', 'month', 'hil']): # "mes", "mensual", "hilabete", etc.
        return 'mes'
    elif any(substring in salary for substring in ['da', "di", "dí", 'egun']): # "day", "día", "diario", etc.
        return 'día'
    elif any(substring in salary for substring in ['ho', 'ordu']): # "hora", "hour", etc.
        return 'hora'
    else:
        return "ERROR"

no_duplicates['Periodicidad'] = no_duplicates['Salario'].apply(extract_periodicity)

# Finally, we create an annual salary column based on the fixed salary and the periodicity.
def extract_annual_salary(salary, periodicity, shift):
    shift = str(shift)
    if salary == None or salary == 'NaN' or periodicity == None or periodicity == 'NaN':
        return None
    elif periodicity == 'año':
        return salary
    elif periodicity == 'mes':
        return salary * 12
    elif periodicity == 'día':
        return salary * 251 # 251 working days per year (2023)
    elif periodicity == 'hora':
        if 'media' in shift.lower():
            return salary * 4 * 251 # suppose a 4-hour workday, and 251 working days per year (2023)
        else:
            return salary * 8 * 251 # suppose an 8-hour workday, and 251 working days per year (2023)
    else:
        return "ERROR"

no_duplicates['Salario anual'] = no_duplicates.apply(lambda row: extract_annual_salary(row['Salario corregido'], row['Periodicidad'], row['Turno']), axis=1)

# Save the processed data to a new file
no_duplicates.to_csv(file_name_no_extension + '-Procesado.csv', encoding='UTF8', sep=',', quotechar='"', index=False)