import re
import os
import json

from xml.dom import minidom


def parse_testr_xml(xml_path, log_dest_dir, json_dest_dir, is_deal_case_name=True, is_rerun=False):
    CASE_SUMMAEY_FILE_NAME = "all_case_summary.json"
    RESULT_PASS = "pass"
    RESULT_FAILURE = "failure"
    RESULT_ERROR = "error"
    RESULT_SKIP = "skip"

    xml_parser = minidom.parse(xml_path)
    test_suite = xml_parser.documentElement
    total = int(test_suite.getAttribute("tests"))
    test_cases = test_suite.getElementsByTagName("testcase")
    success_counter = 0
    error_counter = 0
    failure_counter = 0
    skip_counter = 0
    success_cases = []
    error_cases = []
    failure_cases = []
    skip_cases = []
    all_cases_result = {}
    case_regxp_pattern = re.compile("(.*)\[.+\]")
    reason_regxp_pattern = re.compile("(Details:\s\{.*)")
    for tmp_case in test_cases:
        error_section = tmp_case.getElementsByTagName("error")
        skip_section = tmp_case.getElementsByTagName("skipped")
        failure_section = tmp_case.getElementsByTagName("failure")

        class_name = tmp_case.getAttribute("classname")
        case_name = tmp_case.getAttribute("name")
        regxp_result = case_regxp_pattern.search(case_name)
        if is_deal_case_name and regxp_result is not None:
            case_name = regxp_result.group(1)

        case_full_path = ".".join([class_name, case_name])
        exe_time = tmp_case.getAttribute("time")
        brief_reason = ""
        log_file_full_path = os.path.join(log_dest_dir, case_full_path + ".log")

        if len(error_section) != 0:
            error_cases.append(case_full_path)
            fail_error_reason = error_section[0].childNodes[0].data
            brief_reason = reason_regxp_pattern.search(fail_error_reason).group(1)
            write_reason_file(log_file_full_path, fail_error_reason)
            error_counter += 1
            all_cases_result[case_full_path] = [exe_time, RESULT_ERROR, brief_reason, log_file_full_path]
            continue
        elif len(failure_section) != 0:
            failure_cases.append(case_full_path)
            fail_error_reason = failure_section[0].childNodes[0].data
            brief_reason = reason_regxp_pattern.search(fail_error_reason).group(1)
            write_reason_file(log_file_full_path, fail_error_reason)
            failure_counter += 1
            all_cases_result[case_full_path] = [exe_time, RESULT_FAILURE, brief_reason, log_file_full_path]
            continue
        elif len(skip_section) != 0:
            skip_cases.append(case_full_path)
            brief_reason = skip_section[0].childNodes[0].data
            skip_counter += 1
            all_cases_result[case_full_path] = [exe_time, RESULT_SKIP, brief_reason, ""]
            continue
        else:
            success_cases.append(case_full_path)
            success_counter += 1
            all_cases_result[case_full_path] = [exe_time, RESULT_PASS, brief_reason, ""]

    json_file_full_path = os.path.join(json_dest_dir, CASE_SUMMAEY_FILE_NAME)

    if is_rerun:
        updated_info = update_rerun_result(json_file_full_path, all_cases_result)
        write_json_file(json_file_full_path, updated_info)
    else:
        write_json_file(json_file_full_path, all_cases_result)

    print all_cases_result
    print "total: %d" % total
    _print_case_result(RESULT_PASS, success_counter, success_cases)
    _print_case_result(RESULT_ERROR, error_counter, error_cases)
    _print_case_result(RESULT_FAILURE, failure_counter, failure_cases)
    _print_case_result(RESULT_SKIP, skip_counter, skip_cases)


def write_reason_file(file_full_path, reason):
    log_file = open(file_full_path, "w")
    try:
        log_file.write(reason)
        log_file.flush()
    except Exception, e:
        print "write log file failed, file name: %s" % file_full_path
    finally:
        log_file.close()


def write_json_file(file_full_path, content):
    json_file = open(file_full_path, "w")
    try:
        json_file.write(json.dumps(content, indent=4))
        json_file.flush()
    except Exception, e:
        print "write json file failed, file name: %s" % file_full_path
    finally:
        json_file.close()


def update_rerun_result(file_full_path, updated_cases_dict):
    json_file = open(file_full_path, "r")
    all_info = None
    try:
        all_info = json.load(json_file)
        for key in updated_cases_dict.keys():
            if key not in all_info.keys():
                print "case executed info not found, add case: " % key
            all_info[key] = updated_cases_dict[key]
    except Exception, e:
        print "update rerun result, file name: %s" % file_full_path
    finally:
        json_file.close()
    return all_info


def _print_case_result(case_type, case_count, case_list):
    if case_count != 0:
        print "-" * 40
        print "%s: %d" % (case_type, case_count)
    for case in case_list:
        print case


if __name__ == '__main__':
    parse_testr_xml("/home/xiongjh1/testr_xml.xml", "/home/xiongjh1/", "/home/xiongjh1/")
