import os
import logging
import urllib
import httplib
import json
import ConfigParser

LOG = logging.getLogger('avocado.test')


class ResourceUtils(object):
    def __init__(self, params):
        self.params = params
        self.admin_project = self.params.get('admin_project')
        self.admin_username = self.params.get('admin_username')
        self.admin_password = self.params.get('admin_password')
        self.identity_uri_ip = self.params.get('identity_uri_ip')
        self.identity_port = self.params.get('identity_port')
        self.expect_image = self.params.get('image_name', 'TestVM')
        self.expect_image_alt = self.params.get('image_alt_name', 'TestVM')
        self.expect_public_net = self.params.get('public_net_name',
                                                 'public_net')
        self.expect_share_net = self.params.get('share_net_name', 'share_net')
        self.expect_router = self.params.get('router_name', 'share_router')
        self.expect_flavor_id = self.params.get('flavor_id', '1')
        self.expect_flavor_id_alt = self.params.get('flavor_alt_id', '10')
        self.identity_v2_uri = 'http://' + self.identity_uri_ip + ':' + \
                               self.identity_port + '/v2.0'
        self.identity_v3_uri = 'http://' + self.identity_uri_ip + ':' + \
                               self.identity_port + '/v3'
        self.auth_version = self.params.get('auth_version', 'v3')
        self.http_image = self.params.get('http_image',
                                          '/tmp/tempest/cirros-0.3.4-x86_64-disk.img')
        self.project_network_cidr = self.params.get('project_network_cidr')
        self.scenario_img_dir = self.params.get('scenario_image_dir',
                                                '/tmp/tempest/')
        self.scenario_img_file = self.params.get('scenario_img_file',
                                                 'cirros-0.3.4-x86_64-disk.img')
        self.scenario_img_disk_format = self.params.get(
            'scenario_img_disk_format', 'qcow2')
        self.scenario_img_container_format = self.params.get(
            'scenario_img_container_format', 'bare')
        self.scenario_ami_img_file = self.params.get('scenario_ami_img_file',
                                                     'cirros-0.3.1-x86_64-blank.img')
        self.scenario_ari_img_file = self.params.get('scenario_ari_img_file',
                                                     'cirros-0.3.1-x86_64-initrd')
        self.scenario_aki_img_file = self.params.get('scenario_aki_img_file',
                                                     'cirros-0.3.1-x86_64-vmlinuz')
        self.image_ssh_user = self.params.get('image_ssh_user', 'cirros')
        self.image_ssh_password = self.params.get('image_ssh_password',
                                                  'cubswin:)')
        self.compute_host_count = self.params.get('compute_host_count', '2')
        self.volume_size = self.params.get('volume_size', '70')
        self.tempest_log_file = self.params.get('self.tempest_log_file',
                                                'tempest.log.test')
        self.tempest_log_dir = self.params.get('tempest_log_dir',
                                               '/tmp/tempest_test')

    def get_expected_image_id(self, token, controller_ip,
                              image_name, image_name_alt):
        find_image = False
        find_image_alt = False

        # show all the image list
        params = urllib.urlencode({})
        headers = {"X-Auth-Token": token, "Content-type": "application/json"}
        conn = httplib.HTTPConnection(controller_ip, 9292)
        conn.request("GET", "/v1/images", params, headers)
        response = conn.getresponse()
        data = response.read()
        response_images = json.loads(data)
        conn.close()

        length = len(response_images)

        for i in range(len(response_images['images'])):
            if response_images['images'][i]['name'] == image_name:
                find_image = True
                image_ref_id = response_images['images'][i]['id']
            if response_images['images'][i]['name'] == image_name_alt:
                find_image_alt = True
                image_ref_id_alt = response_images['images'][i]['id']
        if find_image and find_image_alt:
            return image_ref_id, image_ref_id_alt
        else:
            return "None", "None"

    def get_expected_network_id(self, token, controller_ip, public_net_name,
                                share_net_name):
        find_public_net = False
        find_share_net = False

        # show all network list
        params = urllib.urlencode({})
        headers = {"X-Auth-Token": token, "Content-type": "application/json"}
        conn = httplib.HTTPConnection(controller_ip, 9696)
        conn.request("GET", "/v2.0/networks", params, headers)
        response = conn.getresponse()
        data = response.read()
        response_networks = json.loads(data)
        conn.close()

        for i in range(len(response_networks['networks'])):
            if response_networks['networks'][i]['name'] == public_net_name:
                find_public_net = True
                public_net_id = response_networks['networks'][i]['id']
            if response_networks['networks'][i]['name'] == share_net_name:
                find_share_net = True
                share_net_id = response_networks['networks'][i]['id']

        if find_public_net and find_share_net:
            return public_net_id, share_net_id

    def get_expected_router_id(self, token, controller_ip, router_name):
        find_router = False

        # show all router list
        params = urllib.urlencode({})
        headers = {"X-Auth-Token": token, "Content-type": "application/json"}
        conn = httplib.HTTPConnection(controller_ip, 9696)
        conn.request("GET", "/v2.0/routers", params, headers)
        response = conn.getresponse()
        data = response.read()
        response_routers = json.loads(data)
        conn.close()

        for i in range(len(response_routers['routers'])):
            if response_routers['routers'][i]['name'] == router_name:
                find_router = True
                public_router_id = response_routers['routers'][i]['id']

        if find_router:
            return public_router_id

    def get_flavor_count(self, token, controller_ip):
        flavor_count = 0

        # show all router list
        params = urllib.urlencode({})
        headers = {"X-Auth-Token": token, "Content-type": "application/json"}
        conn = httplib.HTTPConnection(controller_ip, 8774)
        conn.request("GET", "/flavors/detail", params, headers)
        response = conn.getresponse()
        data = response.read()
        response_flavors = json.loads(data)
        conn.close()

        flavor_count = len(response_flavors)

        return flavor_count

    def get_compute_host_count(self, token, controller_ip):
        host_count = 0

        # show all host list
        params = urllib.urlencode({})
        headers = {"X-Auth-Token": token, "Content-type": "application/json"}
        conn = httplib.HTTPConnection(controller_ip, 8774)
        conn.request("GET", "/os-hypervisors", params, headers)
        response = conn.getresponse()
        data = response.read()
        response_hosts = json.loads(data)
        conn.close()

        host_count = len(response_hosts['choices'])

        return host_count

    def backup_tempest_config_file(self, config_file, backup_file):
        if os.path.exists(config_file):
            os.rename(config_file, backup_file)
            return True
        else:
            return False

    def get_token(self):
        # connect openstack and get token
        auth_params = '{"auth":{"passwordCredentials":{"username": %s%s%s, ' \
                      '"password": %s%s%s}, "tenantName": %s%s%s }}' % \
                      ("\"", self.admin_username, "\"", "\"", self.admin_password,
                       "\"", "\"", self.admin_project, "\"")
        headers = {"Content-Type": 'application/json'}
        conn = httplib.HTTPConnection(self.identity_uri_ip, self.identity_port)
        conn.request("POST", "/v2.0/tokens", auth_params, headers)
        response = conn.getresponse()
        # response status is not OK
        if response.status != 200:
            LOG.error("Failed to get token from %s:%s with admin_username = %s, "
                      "admin_password = %s and admin_project = %s" %
                      (self.identity_uri_ip, self.identity_port, self.admin_username,
                       self.admin_password, self.admin_project))
            return False
        # when response status is OK, get token from response data
        data = response.read()
        response_data = json.loads(data)
        conn.close()
        apitoken = response_data['access']['token']['id']

        # get image id and alt image id
        image_ref_id, image_ref_id_alt = \
            self.get_expected_image_id(apitoken, self.identity_uri_ip,
                                       self.expect_image, self.expect_image_alt)
        LOG.debug("image_ref_id is %s" % image_ref_id)
        LOG.debug("image_ref_id_alt %s" % image_ref_id_alt)

        # get the public net id
        public_net_id, share_net_id = self.get_expected_network_id(
            apitoken, self.identity_uri_ip,
            self.expect_public_net, self.expect_share_net)
        LOG.debug("public_net_id is %s" % public_net_id)
        LOG.debug("share_net_id is %s" % share_net_id)

        # get the public router id
        public_router_id = self.get_expected_router_id(
            apitoken, self.identity_uri_ip, self.expect_router)
        LOG.debug("public_router_id is %s" % public_router_id)

        # get compute host count
        compute_host_count = self.get_compute_host_count(
            apitoken, self.identity_uri_ip)
        LOG.debug("compute_host_count is %s" % compute_host_count)

        # create tempest log folder and file
        if not os.path.exists(self.tempest_log_dir):
            os.makedirs(self.tempest_log_dir)
            if not os.path.isfile(self.tempest_log_dir +
                                          '/' + self.tempest_log_file):
                f = open(self.tempest_log_dir +
                         '/' + self.tempest_log_file, 'w')
                f.close()
        mount_point = self.params.get('mount_point', '/mnt/share/')
        tempet_resource_dir = mount_point + 'tempest_resource'
        nfs_server_url = self.params.get('nfs_server_url',
                                         '10.100.109.58:/share')

        # mount nfs
        if not os.path.exists(tempet_resource_dir):
            if not os.path.exists(mount_point):
                os.makedirs(mount_point)
            os.system("mount " + nfs_server_url + " " + mount_point)

        # copy image file from nfs for tempest api test
        if not os.path.isfile(self.http_image):
            if not os.path.exists(os.path.dirname(self.http_image)):
                os.makedirs(os.path.dirname(self.http_image))
            os.system("cp " + tempet_resource_dir +
                      self.http_image[len(os.path.dirname(self.http_image)):] +
                      " " + self.http_image)

        # copy image files from nfs for tempest scenario test
        if not os.path.exists(self.scenario_img_dir):
            os.makedirs(os.path.dirname(self.scenario_img_dir))
        for _scenario_image_name_ in \
                [self.scenario_img_file, self.scenario_ami_img_file,
                 self.scenario_ari_img_file, self.scenario_aki_img_file]:
            if not os.path.isfile(self.scenario_img_dir +
                                          _scenario_image_name_):
                os.system("cp " + tempet_resource_dir + "/" +
                          _scenario_image_name_ + " " + self.scenario_img_dir)

        # generate tempest.conf via tempest.conf.sample
        # or exist tempest conf file
        tempest_conf_file = self.params.get('tempest_conf_file',
                                            '/etc/tempest/tempest.conf')
        if not os.path.isfile(tempest_conf_file):
            if not os.path.exists(os.path.dirname(tempest_conf_file)):
                os.makedirs(os.path.dirname(tempest_conf_file))
            os.system("cp " + tempet_resource_dir + "/tempest.conf.sample" +
                      " " + tempest_conf_file)
        else:
            os.system("cp " + tempest_conf_file + " " +
                      tempest_conf_file + ".bak")

        # write /etc/tempest/tempest.conf
        conf = ConfigParser.ConfigParser()
        conf.read(tempest_conf_file)
        conf.set("DEFAULT", "log_file", self.tempest_log_file)
        conf.set("DEFAULT", "log_dir", self.tempest_log_dir)
        conf.set("auth", "admin_username", self.admin_username)
        conf.set("auth", "admin_project_name", self.admin_project)
        conf.set("auth", "admin_password", self.admin_password)
        conf.set("compute", "image_ref", image_ref_id)
        conf.set("compute", "image_ref_alt", image_ref_id_alt)
        conf.set("compute", "flavor_ref", self.expect_flavor_id)
        conf.set("compute", "flavor_ref_alt", self.expect_flavor_id_alt)
        conf.set("compute", "fixed_network_name", self.expect_share_net)
        conf.set("identity", "uri", self.identity_v2_uri)
        conf.set("identity", "uri_v3", self.identity_v3_uri)
        conf.set("identity", "auth_version", self.auth_version)
        conf.set("image", "http_image", self.http_image)
        conf.set("network", "project_network_cidr", self.project_network_cidr)
        conf.set("network", "public_network_id", public_net_id)
        conf.set("network", "floating_network_name", self.expect_public_net)
        conf.set("network", "public_router_id", public_router_id)
        conf.set("scenario", "img_dir", self.scenario_img_dir)
        conf.set("scenario", "img_file", self.scenario_img_file)
        conf.set("scenario", "img_disk_format", self.scenario_img_disk_format)
        conf.set("scenario", "img_container_format",
                 self.scenario_img_container_format)
        conf.set("scenario", "ami_img_file", self.scenario_ami_img_file)
        conf.set("scenario", "ari_img_file", self.scenario_ari_img_file)
        conf.set("scenario", "aki_img_file", self.scenario_aki_img_file)
        conf.set("validation", "image_ssh_user", self.image_ssh_user)
        conf.set("validation", "image_ssh_password", self.image_ssh_password)
        conf.set("volume", "volume_size", self.volume_size)

        try:
            tempest_file = open(tempest_conf_file, "w")
            conf.write(tempest_file)
            tempest_file.close()
        except IOError:
            LOG.debug("Write tempest.conf Error!")

        tempest_file = open(tempest_conf_file, "r")
        try:
            LOG.debug(tempest_file.read())
            return True
        except IOError, e:
            LOG.error("Failed to get content of tempest.conf")
            return False
        finally:
            tempest_file.close()
            if os.path.exists(mount_point):
                os.system("umount " + mount_point)
