TEMPEST_CONF_CONTEXT = """
[DEFAULT]
#debug = true
log_date_format = %Y-%m-%d %H:%M:%S
log_file = tempest.log
log_dir = /tmp/tempest

[alarming]
[auth]

#use_dynamic_credentials = true
#tempest_roles = Member
##tempest_roles = admin
#default_credentials_domain_name = Default
admin_username = admin
admin_project_name = admin
admin_password = admin
admin_domain_name = Default

[baremetal]
[compute]

image_ref = fe1af60e-6fd8-4b30-b1a3-1d6c87ec203a
image_ref_alt = 93446de5-939a-4f1c-98ee-c0f770a812c6
##flavor_ref = 1
##flavor_ref_alt = 10
#fixed_network_name = share_net
fixed_network_name = tempest_net
##endpoint_type = publicURL
##volume_device_name = vdb
min_compute_nodes = 2
#min_microversion = 2.1
#max_microversion = 2.25


[compute-feature-enabled]

resize = true
shelve = false
metadata_service = false
vnc_console = true
personality = false
allow_duplicate_networks = true
config_drive = false
scheduler_available_filters = RetryFilter,AvailabilityZoneFilter,RamFilter,CoreFilter,DiskFilter,ComputeFilter,ComputeCapabilitiesFilter,ImagePropertiesFilter

[dashboard]
[data-processing]
[data-processing-feature-enabled]
[database]
[debug]
[identity]

#disable_ssl_certificate_validation = true
##uri = http://192.168.0.2:5000/v2.0
uri_v3 = http://192.168.0.2:5000/v3
auth_version = v3
#auth_version = v2.0
##region = RegionOne
#v2_admin_endpoint_type = publicURL
v2_admin_endpoint_type = publicURL
##v2_public_endpoint_type = publicURL
v3_endpoint_type = publicURL
##admin_role = admin
admin_domain_scope = True

[identity-feature-enabled]

api_v2 = false
api_extensions = OS-REVOKE,OS-FEDERATION,OS-KSCRUD,OS-SIMPLE-CERT,OS-OAUTH1

[image]

#endpoint_type = publicURL
# http accessible image (string value)
#http_image = http://download.cirros-cloud.net/0.3.1/cirros-0.3.1-x86_64-uec.tar.gz
##http_image = http://10.100.64.7/images/cirros-0.3.4-x86_64-disk.img
##http_image = /var/www/html/images/cirros-0.3.4-x86_64-disk.img
http_image = /tmp/cirros-0.3.4-x86_64-disk.img

[image-feature-enabled]

deactivate_image = true

[input-scenario]

##ssh_user_regex = [["^.*[Cc]irros.*$", "cirros"]]

[negative]

[network]

#project_networks_reachable = true

project_network_cidr = 192.168.141.0/24
public_network_id = b241c043-3b5d-41e8-94dc-56e7f29d24b2
floating_network_name = public_net
public_router_id = a21dcafb-6be6-4213-8988-4ee02d896eef

[network-feature-enabled]

ipv6 = false
api_extensions = dns-integration,ext-gw-mode,binding,metering,agent,subnet_allocation,l3_agent_scheduler,external-net,flavors,fwaasrouterinsertion,net-mtu,quotas,l3-ha,provider,multi-provider,extraroute,portforwarding,fwaas,extra_dhcp_opt,security-group,dhcp_agent_scheduler,rbac-policies,router,allowed-address-pairs

[object-storage]

[object-storage-feature-enabled]

[orchestration]

[oslo_concurrency]

lock_path = /tmp/tempest

[scenario]

img_dir = /opt/images/cirros-0.3.1-x86_64-uec
img_file = cirros-0.3.4-x86_64-disk.img
img_disk_format = qcow2
img_container_format = bare
ami_img_file = cirros-0.3.1-x86_64-blank.img
ari_img_file = cirros-0.3.1-x86_64-initrd
aki_img_file = cirros-0.3.1-x86_64-vmlinuz

[service_available]

neutron = true
swift = false
horizon = false


[stress]

[telemetry]

[telemetry-feature-enabled]

events = true

[validation]

#connect_method = floating
#auth_method = keypair
image_ssh_user = cirros
#run_validation = true
run_validation = true
image_ssh_password = cubswin:)
#floating_ip_range = 172.70.0.200/28
ssh_timeout = 600

[volume]

backend_names = DEFAULT
storage_protocol = ceph
volume_size = 4
##volume_size = 70

[volume-feature-enabled]
multi_backend = false
"""
