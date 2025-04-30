# Read the file
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the first and second occurrences of the route
first_route = '@app.route(\'/staff/all-orders\')'
first_index = content.find(first_route)
second_index = content.find(first_route, first_index + 1)

# Find the end of the second function
function_def = 'def all_staff_orders():'
function_start = content.find(function_def, second_index)
end_index = content.find('return redirect(url_for(\'staff_dashboard\'))', function_start)
# Find the line end after the return statement
end_index = content.find('\n', end_index) + 1

# Remove the duplicate function
if second_index > 0 and end_index > 0:
    new_content = content[:second_index] + content[end_index:]
    # Write the new content
    with open('app_fixed.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Fixed file written to app_fixed.py")
else:
    print("Could not find duplicate function") 