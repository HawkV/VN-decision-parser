import json
import os
import re

vn_address = "C:/Games/Steam/steamapps/workshop/content/236850/684459310"

decision_folder = f"{vn_address}/decisions"

decision_files = [filename for filename in os.listdir(decision_folder) if filename.endswith("txt")]

def array_on_duplicate_keys(ordered_pairs):
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            if type(d[k]) is list:
                d[k].append(v)
            else:
                d[k] = [d[k],v]
        else:
           d[k] = v
    return d

def enquote(matchobj):
    escaped_item = matchobj.group(0).replace('"','\\"')
    return f'"{escaped_item}"'

def brace_commas(matchobj):
    """
        inserting commas after braces
    """
    return matchobj.group(0).replace("}", "},")

def quote_commas(matchobj):
    """
        inserting commas between value and variable name that are enclosed in quotes
        both the ending quote of the value and the beginning quote of the variable
        get into the capture group, so i replace only the first 
        occurrence of a quote with ",
    """
    return matchobj.group(0).replace("\"", "\",", 1)

decisions = {}

for filename in decision_files:
    with open(f"{decision_folder}/{filename}","r") as file:
        string = file.read()
        string = string.replace(":", "@")
        string = string.replace("=", ":")
        string = "{\n " + string + "\n}"

        string = re.sub(r"#.*?\n", "\n", string)
        string = re.sub(r"[@A-Za-z0-9_\.-]+|\"(.+?)\"", enquote, string)
        string = re.sub(r"\}(?![\s]*\})([.\n]+)", brace_commas, string)
        string = re.sub(r"\"([\s]+\")", quote_commas, string)
        string = re.sub(r"}([\s]+\")", brace_commas, string)
        string = re.sub(r"\"([\s]+{)", quote_commas, string)

        data = json.loads(string, object_pairs_hook=array_on_duplicate_keys)
        
        data_decisions = data["country_decisions"]

        for decision in data_decisions:
            decisions[decision] = data_decisions[decision]

#------------------------------------------------------------------

change_tag_decisions = {
    name: decision for name, decision 
    in decisions.items() 
    if "change_tag" in decision["effect"]
}

def list_contains_items(list, items):
    return not set(items).isdisjoint(list)

subject_conditions = ["is_subject", "is_free_or_tributary_trigger"]

free_change_decisions = {
    f"{name}_ai": decision for name, decision
    in change_tag_decisions.items()
    if list_contains_items(decision["allow"], subject_conditions)
}

for decision in free_change_decisions: 
    """removing the conditions from the allow clause"""
    for condition in subject_conditions:
        free_change_decisions[decision]["allow"].pop(condition, None)

    free_change_decisions[decision]["potential"]["ai"] = "yes"

decisions = {"country_decisions": free_change_decisions}

#------------------------------------------------------------------

class MyEncoder(json.JSONEncoder):
    def encode_dict_item(self, key, value, depth):
        if isinstance(value, list):
            return MyEncoder.encode(self, value, key, depth=depth)
        else:
            return """{0}{1}{2}{3}""".format(self.indent * depth, key, self.key_separator, MyEncoder.encode(self, value, key, depth=depth+1))

    def encode(self, obj, key=None, depth=0):
        item_separator = "{0}\n".format(self.item_separator)
        indent = self.indent * depth
        key_separator = self.key_separator

        if isinstance(obj, list):  
            items = item_separator.join(["""{0}{1}{2}{3}""".format(indent, key, key_separator, MyEncoder.encode(self, item, depth=depth+1)) for item in obj])
            return items
        elif isinstance(obj, dict):  
            items = item_separator.join([self.encode_dict_item(key, value, depth) for key, value in obj.items()])
            if depth == 0:
                return items

            return  """{{\n{0}\n{1}}}""".format(items, self.indent * (depth - 1))

        return json.JSONEncoder.encode(self, obj)

updated_string = json.dumps(decisions, indent="\t", separators=("", " = "), cls=MyEncoder)

updated_string = updated_string.replace("@", ":")
updated_string = updated_string.replace("\\\"", "~")
updated_string = updated_string.replace("\"", "")
updated_string = updated_string.replace("~", "\"")
                               

with open("Subject_Decisions.txt", "w") as file:
    file.write(updated_string)
