import json
import os
from git import Repo
import sys
  
     
def get_values_json(payload):
    quotes_payload = json.loads(payload)
    #Extract branch of main repo
    main_branch = quotes_payload['pull_request']
    main_branch = main_branch['base']
    main_branch = main_branch['ref']
    #Extract branch of forked repo
    head_branch = quotes_payload['pull_request']
    head_branch = head_branch['head']
    head_branch = head_branch['ref']
    #Extract name of main repo
    main_repo = quotes_payload['pull_request']
    main_repo = main_repo['base']
    main_repo = main_repo['repo']
    main_repo = main_repo['full_name']
    #Extract name of forked repo
    head_repo = quotes_payload['pull_request']
    head_repo = head_repo['head']
    head_repo = head_repo['repo']
    head_repo = head_repo['full_name']
    #Extract pull request number 
    pull_number = quotes_payload['number']
    
    #Set all the extracted data as outputs 
    #print("::set-output name=baseRef::" + main_branch)
    #print("::set-output name=headRef::" + head_branch)
    #print("::set-output name=baseRepo::" + main_repo)
    #print("::set-output name=headRepo::" + head_repo)
    #print("::set-output name=pullNumber::" + str(pull_number)) 
    return main_repo, main_branch, head_repo, head_branch, pull_number

##################################################################################################################
##################################################################################################################
##################################################################################################################
##################################################################################################################
##################################################################################################################
##################################################################################################################

def repair_file_path(file_path : str) -> str:
    ret = file_path
    # Remove unwanted prefix
    if len(ret) >= 1 and ret[0] == "/":
        ret = ret[1:]
    if len(ret) == 1 and ret[0] == ".":
        ret = ret[1:]
    if len(ret) >= 2 and ret[0] == "." and ret[1] == "/":
        ret = ret[2:]
    # This one is probably redundant.
    if len(ret) >= 1 and ret[0] == "/":
        ret = ret[1:]
    return ret

def repair_folder_path(folder_path: str) -> str:
    ret = repair_file_path(folder_path)
    # Add desired postfix
    if len(ret) >= 1 and ret[-1] != "/":
        ret += "/" 
    return ret

# Returns all file additions that were made within the base folder. 
# The added files are returned as lists of the folders (and file name) constituting their paths.
# E.g. a file "fol1/fol2/fol3/file1.txt" is represented as ["fol1", "fol2", "fol3", "file1.txt"]
def extract_candidates(file_additions : "list of str", base_folder_segments : "list of str") -> "list of lists of str":
    ret = [] 
    for file_path in file_additions:
        path_segments = file_path.split("/")
        is_candidate = True
        for j, base_segment in enumerate(base_folder_segments):
            if(base_segment != path_segments[j]):
                is_candidate = False
                break
        if is_candidate:
            ret.append(path_segments)
    return ret

# Returns the files which are named "README.md" (capitalization doesn't matter)
def extract_readme(candidates : "list of lists of str") -> "list of lists of str":
    return [e for e in candidates if e[-1].lower() == "readme.md"]

# Given a string "name1-name2-...", returns a list of all strings that are seperated by a hyphen. 
# The strings are also sorted so that e.g. "name1-name2" and "name2-name1" are considered equal. 
def extract_and_sort_names(folder_name : str) -> "list of str":
    l = folder_name.split("-")
    l.sort()
    return l

# Returns true if the readme contains KTH mail addresses corresponding to the ID:s extracted from its parent folder name.
def readme_is_valid(id_list : "list of str", readme_path : str) -> bool:
    file_content = []
    with open(readme_path, 'r') as f:
        file_content = f.read()
    is_valid = True
    for kth_id in id_list:
        if kth_id + "@kth.se" not in file_content:
            is_valid = False
            break
    return is_valid

##################################################################################################################
##################################################################################################################
##################################################################################################################
##################################################################################################################
##################################################################################################################
##################################################################################################################

# Returns the possible sorted subgroups, including the empty group as the first entry. Thus [1:] will return groups of at least one element.
# Member inclusions can be set as list of ints. This will make it so that the index of the member inclusions list will indicate whether to include 
# a particular member when creating subgroups or not. An int of at least 1 is required to include the member.
def subgroups_recursion(group_members: "list of str", index : int, member_inclusions=None) -> "list of lists of str":
    if index >= len(group_members):
        return [[]]
    subgroups = subgroups_recursion(group_members, index + 1, member_inclusions=member_inclusions)
    additions = []
    if member_inclusions == None or member_inclusions[len(group_members) - 1 - index] > 0:
        for l in subgroups:
            new_entry = l.copy()
            new_entry.append(group_members[len(group_members) - 1 - index])
            additions.append(new_entry)
    return subgroups + additions

# Returns a list of tuples with the number of collaborations among the subgroups of the group members, along with which group members are part of this.
# The subgroups considered are at least of size 2.
# The special case of a group with a single members does not count as a subset to anything else but itself.
def most_collaborations(base_folder : str, group_members : "list of str") -> "list of pairs (int, list of str)":
    # https://stackoverflow.com/questions/973473/getting-a-list-of-all-subdirectories-in-the-current-directory 
    folder_lists = [x[1] for x in os.walk(base_folder) if x[1] != []]
    folders = [item for sublist in folder_lists for item in sublist]
    
    subgroupsR = subgroups_recursion(group_members, 0)
    subgroups = [sub for sub in subgroupsR if len(sub) > 1]

    subgroups_map = {}
    for sub in subgroups:
        subgroups_map["-".join(sub)] = 0

    if len(group_members) == 1:
        counter = 0
        for f in folders:
            if f == group_members[0]:
                counter += 1
        return [(counter, [group_members[0]])]

    for f in folders:
        name_inclusions = [0 for _ in group_members]
        names = extract_and_sort_names(f)
        for n1 in names:
            for i, n2 in enumerate(group_members):
                if n1 == n2:
                    name_inclusions[i] += 1
        keysR = subgroups_recursion(group_members, 0, member_inclusions=name_inclusions)
        keys = ["-".join(key) for key in keysR if len(key) > 1]
        for key in keys:
            subgroups_map[key] += 1
        
    ret_list = []
    for sub in subgroups:
        ret_list.append((subgroups_map["-".join(sub)], sub))
    return ret_list

def write_json_output(report : str, is_valid_pull_request : bool, pr_number : int, is_student_submission : bool, ids_match : bool, valid_group : bool) -> "no return":
    print(json.dumps({"report":report, 
                      "valid_pr":("true" if is_valid_pull_request else "false"),
                      "pr_num":pr_number,
                      "student_submission":("true" if is_student_submission else "false"),
                      "ids_match":("true" if ids_match else "false"),
                      "valid_group":("true" if valid_group else "false")
                      }))

# Expects six command line arguments in the following order: 
# - a github access token
# - the pull request payload as a json object
# - paths of files that have been added on the form [file1_path,file2_path,...] or ["file1_path","file2_path","..."] . 
# - the path to the base folder, which is the folder that is to be considered root when running this script. 
# - an int with the maximum group size,
# - and an int with the maximum number of times the same group is allowed to work together (this includes groups of only a single person).
# 
# For all paths specified, they should not begin with a "./" but every other folder in the path should be followed by "/" . 
# E.g. "fol/base_folder/" . 
# Pointing to current directory would be just the empty string "".
# However, even if the input deviates from this it's attempted to repair it.
def main() -> "no return":
    report = ""
    verdict = ""
    is_valid_pull_request = True
    is_student_submission = False
    valid_readme = False
    valid_group = False

    folder_name = ""


    #path = sys.argv[1]
    #with open(path, 'r') as myfile:
    #  data=myfile.read()
    payload = sys.argv[2]
    try:
        main_repo, main_branch, head_repo, head_branch, pull_number = get_values_json(payload)
    except: 
        #print("::set-output name=isPullReq::" + "false")
        is_valid_pull_request = False
        write_json_output(report, is_valid_pull_request, pull_number, is_student_submission, valid_readme, valid_group)
        return

    
    # using an access token
    # https://<token>@github.com/owner/repo.git
    # 'http://user:password@github.com/user/project.git'
    repo = Repo.clone_from("https://" + sys.argv[1] + "@github.com/" + head_repo + ".git", '../', branch=head_branch)
    ###########################################################################
    #file_additions = sys.argv[1][1:-1].split(",")
    file_additions = sys.argv[3][1:-1].split(",")
    for i, f in enumerate(file_additions):
        file_additions[i] = repair_file_path(f)
    #base_folder = sys.argv[2]
    base_folder = sys.argv[4]
    base_folder = repair_folder_path(base_folder)
    base_folder_segments = base_folder.split("/")[:-1]
    candidates = extract_candidates(file_additions, base_folder_segments)
    readme_list = extract_readme(candidates)

    if len(readme_list) != 1:
        report += "There wasn't exactly one readme added under \"" + base_folder + "\" . This is assumed not to be a student submission.\n"
        is_student_submission = False
    else:
        is_student_submission = True
        #print("::set-output name=folderName::" + readme_list[0][-2])
        folder_name = readme_list[0][-2]
        id_list = extract_and_sort_names(readme_list[0][-2]) # There is only one readme, and the ID:s should be in the immediate parent folder name.
        #is_valid = readme_is_valid(id_list, "/".join(readme_list[0]))   
        is_valid = readme_is_valid(id_list, "../" + head_repo.split("/")[1] + "/".join(readme_list[0]))   
        if is_valid:
            report +=  "The ID:s constituting the folder name matched with the email addresses in the README file.\n"
            valid_readme = True
        else:
            report += "The ID:s constituting the folder name did not match with the email addresses in the README file. "
            report += "If this is a student submission, please revise the pull request.\n" 
            valid_readme = False

    #print("::set-output name=report::" + report)
    #print("::set-output name=idsMatch::" + ("true" if valid_readme else "false"))
    if not is_student_submission or not valid_readme:
        write_json_output(report, is_valid_pull_request, pull_number, is_student_submission, valid_readme, valid_group)
        return
    ###########################################################################

    group_members = extract_and_sort_names(folder_name)
    collaborations = most_collaborations(base_folder, group_members)
    allowed_group_size = int(sys.argv[5])
    allowed_collaboration_times = int(sys.argv[6])

    valid_group = True
    for num, members in collaborations:
        if num >= allowed_collaboration_times:
            verdict += "The group consisting of " 
            for g in members:
                verdict += g + ", "
            verdict += "appears to have worked together " + str(num) + " times, while the maximum allowed is " + str(allowed_collaboration_times) + ". "
            verdict += "Consequently they may not work together here.\n"
            valid_group = False

        report += "The group consisting of " 
        for g in members:
            report += g + ", "
        report += "appears to have worked together "  + str(num) + " times.\n"
    report += "Maximum group size allowed: " + str(allowed_group_size) + ".\n"
    report += "Maximum number of collaborations allowed: " + str(allowed_collaboration_times) + ".\n"

    
    if len(group_members) > allowed_group_size:
        verdict += "The group size is " + str(len(group_members))
        verdict += ", but the maximum allowed group size is " + str(allowed_group_size) + ". This group is thus not allowed.\n"
        valid_group = False
    
    if len(verdict) == 0:
        verdict += "The group composition is allowed.\n"
    #print("::set-output name=groupValidityReport::" + report + verdict)
    #print("::set-output name=groupValidity::" + ("true" if valid_group else "false"))
    #print(json.dumps({"report":report+verdict, "validity":("true" if valid_group else "false")}))
    write_json_output(report + verdict, is_valid_pull_request, pull_number, is_student_submission, valid_readme, valid_group)

if __name__ == "__main__":
    main()