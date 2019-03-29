CEPH_TEST_REPORT = """
<html>
<head>
<meta charset="utf-8">
<title>JOB REPORT</title>
</head>
<body>

<h3>Lenovo ThinkCloud SDS REST API Test Result</h3>
 <h4 >Summary</h4>
             <table border="1">
                 % for product_version, casename, result, passed, failed, errors, test_total_time, time_start, time_end, logdir in items:
                <tr>
                    <td>Product Version</td><td><tt>{{product_version}}</tt></td>
                </tr>
                 <tr>
                     <td>Test Plan Name</td><td><tt>{{casename}}</tt></td>
                 </tr>
                 <tr>
                     <td>Result</td><td><tt>{{result}} (Passed: {{passed}}; Failed: {{failed}}; Errors: {{errors}})</tt></td>
                 </tr>
                 <tr>
                     <td>Start Time</td><td><tt>{{time_start}}</tt></td>
                 </tr>
                 <tr>
                     <td>End Time</td><td><tt>{{time_end}}</tt></td>
                 </tr>
                <tr>
                     <td>Cumulative Time</td><td><tt>{{test_total_time}}</tt></td>
                </tr>
                 <tr>
                     <td>Result Link</td><td><tt>{{logdir}}</tt></td>
                 </tr>
                 %end
             </table>
 </html>
 """

CEPH_TEST_DETAIL_REPORT = """
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta httfrom commands import *p-equiv="Content-Type" content="text/html; charset=UTF-8">
<style type="text/css">
    table.gridtable {
        font-family:Verdana,Helvetica,sans serif;
        font-size:12px;
        color:#333333;
        border-width: 1px;
        border-color: #666666;
        border-collapse: collapse;
    }
    table.gridtable tr th {
        font-family:Verdana,Helvetica,sans serif;
        font-size:12px;
        border-width: 1px;
        padding: 2px;
        border-style: solid;
        border-color: #666666;
        background-color: #3399ff;
    }
    table.gridtable td {
        font-family:Verdana,Helvetica,sans serif;
        font-size:12px;
        border-width: 1px;
        padding: 2px;
        border-style: solid;
        border-color: #666666;
        background-color: #ffffff;
    }
    table.summarytable {
        font-family:Verdana,Helvetica,sans serif;
        font-size:12px;
        color:#333333;
        border-width: 1px;
        border-color: #666666;
        border-collapse: collapse;
    }
    .special{
        font-family:Verdana,Helvetica,sans serif;
        font-size: 14px;
        color:black;
    }
    .text{
        font-family:Verdana,Helvetica,sans serif;
        font-size: 12px;
        color:black;
        margin-left: 15px;
    }
    body {font-family:Verdana,Helvetica,sans serif;
          font-size:12px;
          color:black;
    }
</style>

<title>JOB REPORT</title>
</head>
<body>
<p class="text" style="margin-left:0px">
Dear ALL,
<br/>
<br/>
% for item in items:
<tr>
Please find the CICD pipeline report for this build below: {{item[0]}}
</tr>
% end

</p><br/>

<li><b>Deployment</b></li><br/><br/>
<p style="margin-left: 15px">
 <table>
 % for env, URL, deploy_result, ha_install in deployments:
 <tr>
 <td>ENV: </td><td>{{env}}<td>
 </tr>
 <tr><td>URL: </td><td>{{URL}}<td></tr>
 % end
 % if ha_install == 'true':
     % if deploy_result == 'PASS':
         <tr><td>Deployment Result(HA): </td><td><font color="green">{{deploy_result}}</font><td></tr>
         <tr><td>Deployment Result(Non HA): </td><td><font color="green">Not Start</font><td></tr>
     % else:
         <tr><td>Deployment Result(HA): </td><td><font color="red">{{deploy_result}}</font><td></tr>
         <tr><td>Deployment Result(Non HA): </td><td><font color="green">Not Start</font><td></tr>
     % end
 % elif ha_install == 'false':
     % if deploy_result == 'PASS':
         <tr><td>Deployment Result(HA): </td><td><font color="red">FAILED</font><td></tr>
         <tr><td>Deployment Result(Non HA): </td><td><font color="green">{{deploy_result}}</font><td></tr>
     % else:
         <tr><td>Deployment Result(HA): </td><td><font color="red">FAILED</font><td></tr>
         <tr><td>Deployment Result(Non HA): </td><td><font color="red">{{deploy_result}}</font><td></tr>
     % end     
 % else:
     % if deploy_result == 'PASS':
         <tr><td>Deployment Result: </td><td><font color="green">{{deploy_result}}</font><td></tr>
     % else:
         <tr><td>Deployment Result: </td><td><font color="red">{{deploy_result}}</font><td></tr>
     % end
 % end

 </table>
</p><br/><br/>

             <li><b>RESTful API Automation Test Summary</b></li><br/><br/>
             <p style="margin-left: 15px">
             <table class="gridtable">
                 % for product_version, casename, result, passed, failed, errors, test_total_time, time_start, time_end, logdir in items:
                <tr>
                    <td style="font-weight:normal">Product Version</td><td>{{product_version}}</td>
                </tr>
                 <tr>
                     <td>Test Plan Name</td><td>{{casename}}</td>
                 </tr>
                 <tr>
                     <td>Result</td><td>{{result}} (Passed: {{passed}}; Failed: {{failed}}; Errors: {{errors}})</td>
                 </tr>
                 <tr>
                     <td>Start Time</td><td>{{time_start}}</td>
                 </tr>
                 <tr>
                     <td>End Time</td><td>{{time_end}}</td>
                 </tr>
                <tr>
                     <td>Cumulative Time</td><td>{{test_total_time}}</td>
                </tr>
                 <tr>
                     <td>Result Link</td><td>{{logdir}}</td>
                 </tr>
                 %end
             </table>
             </p>
             </br>
             </br>

             <li><b>RESTful API Automation Test Report</b></li><br/><br/>
             <p style="margin-left: 15px">
             <table class="gridtable">
                 <tr>
                     <th style="font-weight:bold">Suite</th>
                     <th style="font-weight:bold">Pass</th>
                     <th style="font-weight:bold">Fail</th>
                     <th style="font-weight:bold">Error</th>
                 </tr>
                 % for test_results in details:
                     % for test_result in test_results:
                     <tr>
                         <td>{{test_result[0]}}</td>
                         <td>{{test_result[1]}}</td>
                         <td>{{test_result[2]}}</td>
                         <td>{{test_result[3]}}</td>
                     </tr>
                     % end
                 % end
             </table>
             </p>
             </br>

             <li><b>Daily Build Location:</b></li><br/>
             <p class="text">{{build_location}}</p></br>

             <li><b>Code Manifest:</b></li><br/>
             <p class="text">{{code_mainfest}}</p></br>

             <li><b>New Patch List:</b></li><br/>
             <p class="text">
             % for new_patch in new_patch_list:
                 {{new_patch}}<br/>
             % end
             </p>
             </br>


<p><font color="gray" size="2px">
Best Regards,<br/>
CloudTest Team<br/>
</font></p>

</body>
</html>

 """


TEMPEST_TEST_REPORT = """
<html>
<head>
<meta charset="utf-8">
<title>JOB REPORT</title>
</head>
<body>

<h3>Lenovo ThinkCloud Integrate Test Result</h3>

<h4 >Summary</h4>
            <table border="1">
                % for product_version, casename, result, passed, failed, errors, test_total_time, time_start, time_end,logdir in items:
                <tr>
                    <td>Product Version</td><td><tt>{{product_version}}</tt></td>
                </tr>
                <tr>
                    <td>Test Plan Name</td><td><tt>{{casename}}</tt></td>
                </tr>
                <tr>
                    <td>Result</td><td><tt>{{result}} (Passed: {{passed}}; Failed: {{failed}}; Errors: {{errors}})</tt></td>
                </tr>
                <tr>
                    <td>Start Time</td><td><tt>{{time_start}}</tt></td>
                </tr>
                <tr>
                    <td>End Time</td><td><tt>{{time_end}}</tt></td>
                </tr>
                <tr>
                    <td>Cumulative Time</td><td><tt>{{test_total_time}}</tt></td>
                </tr>
                <tr>
                    <td>Result Link</td><td><tt>{{logdir}}</tt></td>
                </tr>
                %end
            </table>
</html>
"""


RALLY_TEST_REPORT = """
<html>
<head>
<meta charset="utf-8">
<title>JOB REPORT</title>
</head>
<body>

<h3>Lenovo ThinkCloud Performance Test Result</h3>

<h4 >Summary</h4>
            <table border="1">
                % for product_version, casename, result, passed, failed, errors, test_total_time, time_start, time_end,logdir in items:
                <tr>
                    <td>Product Version</td><td><tt>{{product_version}}</tt></td>
                </tr>
                <tr>
                    <td>Test Plan Name</td><td><tt>{{casename}}</tt></td>
                </tr>
                <tr>
                    <td>Result</td><td><tt>{{result}} (Passed: {{passed}}; Failed: {{failed}}; Errors: {{errors}})</tt></td>
                </tr>
                <tr>
                    <td>Start Time</td><td><tt>{{time_start}}</tt></td>
                </tr>
                <tr>
                    <td>End Time</td><td><tt>{{time_end}}</tt></td>
                </tr>
                <tr>
                    <td>Cumulative Time</td><td><tt>{{test_total_time}}</tt></td>
                </tr>
                <tr>
                    <td>Result Link</td><td><tt>{{logdir}}</tt></td>
                </tr>
                %end
            </table>
</html>
"""


COMMON_TEST_REPORT = """
<html>
<head>
<meta charset="utf-8">
<title>JOB REPORT</title>
</head>
<body>

<h3>Lenovo ThinkCloud Test Result</h3>

<h4 >Summary</h4>
            <table border="1">
                % for product_version, casename, result, passed, failed, errors, test_total_time, time_start, time_end,logdir in items:
                <tr>
                    <td>Product Version</td><td><tt>{{product_version}}</tt></td>
                </tr>
                <tr>
                    <td>Test Plan Name</td><td><tt>{{casename}}</tt></td>
                </tr>
                <tr>
                    <td>Result</td><td><tt>{{result}} (Passed: {{passed}}; Failed: {{failed}}; Errors: {{errors}})</tt></td>
                </tr>
                <tr>
                    <td>Start Time</td><td><tt>{{time_start}}</tt></td>
                </tr>
                <tr>
                    <td>End Time</td><td><tt>{{time_end}}</tt></td>
                </tr>
                <tr>
                    <td>Cumulative Time</td><td><tt>{{test_total_time}}</tt></td>
                </tr>
                <tr>
                    <td>Result Link</td><td><tt>{{logdir}}</tt></td>
                </tr>
                %end
            </table>
</html>
"""


NFV_TEST_REPORT = """
<html>
<head>
<meta charset="utf-8">
<title>JOB REPORT</title>
</head>
<body>

<h3>Lenovo ThinkCloud NFVi Test Result</h3>

<h4 >Summary</h4>
            <table border="1">
                % for product_version, casename, result, passed, failed, errors, test_total_time, time_start, time_end,logdir in items:
                <tr>
                    <td>Product Version</td><td><tt>{{product_version}}</tt></td>
                </tr>
                <tr>
                    <td>Test Plan Name</td><td><tt>{{casename}}</tt></td>
                </tr>
                <tr>
                    <td>Result</td><td><tt>{{result}} (Passed: {{passed}}; Failed: {{failed}}; Errors: {{errors}})</tt></td>
                </tr>
                <tr>
                    <td>Start Time</td><td><tt>{{time_start}}</tt></td>
                </tr>
                <tr>
                    <td>End Time</td><td><tt>{{time_end}}</tt></td>
                </tr>
                <tr>
                    <td>Cumulative Time</td><td><tt>{{test_total_time}}</tt></td>
                </tr>
                <tr>
                    <td>Result Link</td><td><tt><a href="{{logdir}}">{{logdir}}</a></tt></td>
                </tr>
                %end
            </table>
</html>
"""
