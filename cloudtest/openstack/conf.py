import os
import logging
import ConfigParser
from cloudtest import utils_misc
from image import Image
from cloudtest.openstack.network import Network
from compute import Compute
from keystone import Keystone
from cloudtest.resources import tempest_conf

LOG = logging.getLogger('avocado.test')


class ConfigBase(object):
    def __init__(self, params):
        self.params = params
        self.admin_username = self.params.get('admin_username')
        self.admin_password = self.params.get('admin_password')
        self.admin_tenant_name = self.params.get('admin_tenant_name')
        self.uri = self.params.get('OS_AUTH_URL')
        self.uri_v3 = self.params.get('uri_v3')
        self.http_image = self.params.get('http_image', '')
        self.http_url = self.params.get('http_url', '')

    def save_conf_file(self, conf_path, conf_parser, dbginfo, errinfo):
        """
        Save config data to file
        :param conf_path: config file path
        :param conf_parser: config file data
        :param dbginfo: debug info for save config file
        :param errinfo: error info for save config file
        """
        try:
            conf_file = open(conf_path, "w")
            conf_parser.write(conf_file)
            conf_file.close()
        except IOError:
            LOG.debug(dbginfo)

        conf_file = open(conf_path, "r")
        try:
            LOG.debug(conf_file.read())
            return True
        except IOError, e:
            LOG.error(errinfo)
            return False
        finally:
            conf_file.close()

    def prepare_images(self, location_src, location_tag, files):
        """
        Copy image files from source to target
        """
        if not os.path.exists(location_tag):
            os.makedirs(os.path.dirname(location_tag))
        for _image_name_ in files:
            if not os.path.isfile(location_tag + _image_name_):
                os.system("wget " + location_src + _image_name_ +
                          " --directory-prefix=" + location_tag)


class ConfigTempest(ConfigBase):
    def __init__(self, params):
        super(ConfigTempest, self).__init__(params)
        self.params = params
        self.image_ref = ""
        self.image_ref_name = self.params.get('image_ref_name',
                                              'TestVM')
        self.image_ref_dep = self.params.get('image_ref_dep',
                                             'Image')
        self.image_ref_key = self.params.get('image_ref_key',
                                             'image_ref_path')
        self.image_ref_path = self.params.get('image_ref_path', '')
        self.image_ref_alt = ""
        self.image_ref_alt_name = self.params.get('image_ref_alt_name',
                                                  'TestVM')
        self.image_ref_alt_dep = self.params.get('image_ref_alt_dep',
                                                 'Image')
        self.image_ref_alt_key = self.params.get('image_ref_alt_key',
                                                 'image_ref_alt_path')
        self.image_ref_alt_path = self.params.get('image_ref_alt_path', '')
        self.image_ssh_user = self.params.get('image_ssh_user', 'cirros')
        self.image_ssh_password = self.params.get('image_ssh_password',
                                                  'cubswin:)')
        self.public_network_name = self.params.get('public_network_name',
                                                   'public_net')
        self.public_network_id = ''
        self.fixed_network_name = self.params.get('fixed_network_name',
                                                  'cloudtest_tempest_net')
        self.floating_network_name = self.params.get('floating_network_name',
                                                     'public_net')
        self.public_router_name = self.params.get('public_router_name', '')
        self.public_router_id = ''
        self.flavor_ref_name = self.params.get('flavor_ref_name', '')
        self.flavor_ref = ''
        self.flavor_ref_alt_name = self.params.get('flavor_ref_alt_name', '')
        self.flavor_ref_alt = ''
        self.auth_version = self.params.get('auth_version', 'v3')
        self.v2_admin_endpoint_type = self.params.get('v2_admin_endpoint_type'
                                                      ,'adminURL')
        self.project_network_cidr = self.params.get('project_network_cidr')
        self.api_v2 = self.params.get('api_v2', 'true')
        self.img_dir = self.params.get('img_dir', '/tmp/tempest/')
        self.img_file = self.params.get('img_file',
                                        'cirros-0.3.4-x86_64-disk.img')
        self.img_disk_format = self.params.get('img_disk_format', 'qcow2')
        self.img_container_format = self.params.get('img_container_format',
                                                    'bare')
        self.ami_img_file = self.params.get('ami_img_file',
                                            'cirros-0.3.1-x86_64-blank.img')
        self.ari_img_file = self.params.get('ari_img_file',
                                            'cirros-0.3.1-x86_64-initrd')
        self.aki_img_file = self.params.get('aki_img_file',
                                            'cirros-0.3.1-x86_64-vmlinuz')
        self.compute_host_count = self.params.get('compute_host_count', '2')
        self.volume_size = self.params.get('volume_size', '70')
        self.log_file = self.params.get('log_file', 'tempest.log')
        self.log_dir = self.params.get('log_dir', '/tmp/tempest')

    def set_resources(self):
        """
        Prepare some values that include:
        image_ref, get an image id and set to image_ref.
                        if the image not existing, create it.
        image_ref_alt, get another image id and set to image_ref_alt.
                        if the image not existing, create it.
        public_network_id,  get public network id and
                        set to public_network_id.
        fixed_network_name, retrieve a fixed network name
                        and set to fixed_network_name,
                        if the network not existing, create it.
        public_router_id, get public router id and set to public_router_id.
                        if the router not existing, create it.
        flavor_ref, get a flavor id and set to flavor_ref.
        flavor_ref_alt, get another flavor id and set to flavor_ref_alt.
        compute_host_count, get the count of the compute host
                        and set to compute_host_count
        """
        image = Image(self.params)
        net = Network(self.params)
        compute = Compute(self.params)
        utils_misc.set_openstack_environment()
        # get image id and alt image id
        image_ref = image.get_image_id(self.image_ref_name)
        if image_ref is None:
            self.image_ref_path = os.environ["image_ref_path"]
            image_ref = image.create_image(self.image_ref_name,
                                           self.image_ref_path)
        self.image_ref = image_ref
        LOG.info("image_ref is %s" % self.image_ref)

        image_ref_alt = image.get_image_id(self.image_ref_alt_name)
        if image_ref_alt is None:
            self.image_ref_alt_path = os.environ["image_ref_alt_path"]
            image_ref_alt = image.create_image(self.image_ref_alt_name,
                                               self.image_ref_alt_path)
        self.image_ref_alt = image_ref_alt
        LOG.info("image_ref_alt is %s" % self.image_ref_alt)

        # get the public net id
        self.public_network_id = net.get_network_id(
            self.public_network_name)
        LOG.info("public_network_id is %s" % self.public_network_id)

        # get network and create it if it does not existing.
        fixed_network = net.get_network(self.fixed_network_name)
        if fixed_network is None:
            LOG.info('Creating fixed network: %s' % self.fixed_network_name)
            net.create_network(name=self.fixed_network_name, subnet=True)
        LOG.info("fixed_network_name is %s" % self.fixed_network_name)

        # get the public router id
        public_router_id = net.get_router_id(self.public_router_name)
        if public_router_id is None:
            public_router = net.create_router(
                {"name": self.public_router_name}, True)
            public_router_id = public_router["router"]["id"]
        self.public_router_id = public_router_id
        LOG.info("public_router_id is %s" % self.public_router_id)

        # get flavor id
        self.flavor_ref = compute.get_flavor_id(self.flavor_ref_name)
        LOG.info("flavor_ref is %s" % self.flavor_ref)
        self.flavor_ref_alt = compute.get_flavor_id(
            self.flavor_ref_alt_name)
        LOG.info("flavor_ref_alt is %s" % self.flavor_ref_alt)

        # get compute host count
        self.compute_host_count = compute.get_compute_host_count()
        LOG.info("compute_host_count is %s" % self.compute_host_count)

    def backup_tempest_config_file(self, config_file, backup_file):
        """
        Backup tempest config file
        :param config_file: config file path
        :param backup_file: backup file path
        """
        if os.path.exists(config_file):
            os.rename(config_file, backup_file)
            return True
        else:
            return False

    def prepare_tempest_log(self):
        """
        Create tempest log folder and file
        """
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            if not os.path.isfile(self.log_dir +
                                          '/' + self.log_file):
                f = open(self.log_dir +
                         '/' + self.log_file, 'w')
                f.close()

    def prepare_images_tempest(self):
        files = [self.img_file, self.ami_img_file,
                 self.ari_img_file, self.aki_img_file]
        self.prepare_images(self.http_url, self.img_dir, files)

    def prepare_conf_file(self, conf_path):
        """
        Generate config file base on sample file
        or backup existing config file
        :param conf_path: the sample for config file
        """
        if not os.path.isfile(conf_path):
            if not os.path.exists(os.path.dirname(conf_path)):
                os.makedirs(os.path.dirname(conf_path))
            fp = open(conf_path, "w")
            fp.write(tempest_conf.TEMPEST_CONF_CONTEXT)
            fp.close()
        else:
            os.system("cp " + conf_path + " " +
                      conf_path + ".bak")

    def gen_tempest_conf(self):
        """
        Generate tempest config
        """
        conf_path = self.params.get('conf_file',
                                    '/etc/tempest/tempest.conf')
        self.prepare_conf_file(conf_path)

        # write /etc/tempest/tempest.conf
        conf = ConfigParser.ConfigParser()
        conf.read(conf_path)
        conf.set("DEFAULT", "log_file", self.log_file)
        conf.set("DEFAULT", "log_dir", self.log_dir)
        conf.set("auth", "admin_username", self.admin_username)
        conf.set("auth", "admin_tenant_name", self.admin_tenant_name)
        conf.set("auth", "admin_project_name", self.admin_tenant_name)
        conf.set("auth", "admin_password", self.admin_password)
        conf.set("compute", "image_ref", self.image_ref)
        conf.set("compute", "image_ref_alt", self.image_ref_alt)
        conf.set("compute", "flavor_ref", self.flavor_ref)
        conf.set("compute", "flavor_ref_alt", self.flavor_ref_alt)
        conf.set("compute", "fixed_network_name", self.fixed_network_name)
        conf.set("compute", "min_compute_nodes", self.compute_host_count)
        conf.set("identity", "uri", self.uri)
        conf.set("identity", "uri_v3", self.uri_v3)
        conf.set("identity", "auth_version", self.auth_version)
        conf.set("identity", "v2_admin_endpoint_type",
                 self.v2_admin_endpoint_type)
        conf.set("identity-feature-enabled", "api_v2", self.api_v2)
        conf.set("image", "http_image", self.http_image)
        conf.set("network", "project_network_cidr",
                 self.project_network_cidr)
        conf.set("network", "public_network_id", self.public_network_id)
        conf.set("network", "floating_network_name",
                 self.floating_network_name)
        conf.set("network", "public_router_id", self.public_router_id)
        conf.set("scenario", "img_dir", self.img_dir)
        conf.set("scenario", "img_file", self.img_file)
        conf.set("scenario", "img_disk_format", self.img_disk_format)
        conf.set("scenario", "img_container_format",
                 self.img_container_format)
        conf.set("scenario", "ami_img_file", self.ami_img_file)
        conf.set("scenario", "ari_img_file", self.ari_img_file)
        conf.set("scenario", "aki_img_file", self.aki_img_file)
        conf.set("validation", "image_ssh_user", self.image_ssh_user)
        conf.set("validation", "image_ssh_password",
                 self.image_ssh_password)
        conf.set("volume", "volume_size", self.volume_size)

        self.save_conf_file(conf_path, conf,
                            "Write tempest.conf Error!",
                            "Failed to get content of tempest.conf")

    def list_conf(self):
        LOG.info("--------------------------------")
        LOG.info("compute_host_count            %s" % self.compute_host_count)
        LOG.info("[DEFAULT]")
        LOG.info("log_file                      %s" % self.log_file)
        LOG.info("log_dir                       %s" % self.log_dir)
        LOG.info("[auth]")
        LOG.info("admin_username                %s" % self.admin_username)
        LOG.info("admin_tenant_name             %s" % self.admin_tenant_name)
        LOG.info("admin_password                %s" % self.admin_password)
        LOG.info("[compute]")
        LOG.info("image_ref                     %s" % self.image_ref)
        LOG.info("image_ref_name                %s" % self.image_ref_name)
        LOG.info("image_ref_path                %s" % self.image_ref_path)
        LOG.info("image_ref_alt                 %s" % self.image_ref_alt)
        LOG.info("image_ref_alt_name            %s" % self.image_ref_alt_name)
        LOG.info("image_ref_alt_path            %s" % self.image_ref_alt_path)
        LOG.info("flavor_ref                    %s" % self.flavor_ref)
        LOG.info("flavor_ref_name               %s" % self.flavor_ref_name)
        LOG.info("flavor_ref_alt                %s" % self.flavor_ref_alt)
        LOG.info("flavor_ref_alt_name           %s" % self.flavor_ref_alt_name)
        LOG.info("fixed_network_name            %s" % self.fixed_network_name)
        LOG.info("[identity]")
        LOG.info("uri                           %s" % self.uri)
        LOG.info("uri_v3                        %s" % self.uri_v3)
        LOG.info("auth_version                  %s" % self.auth_version)
        LOG.info("[image]")
        LOG.info("http_image                    %s" % self.http_image)
        LOG.info("[network]")
        LOG.info("public_network_name           %s" % self.public_network_name)
        LOG.info("public_network_id             %s" % self.public_network_id)
        LOG.info("floating_network_name         %s" % self.floating_network_name)
        LOG.info("public_router_name            %s" % self.public_router_name)
        LOG.info("public_router_id              %s" % self.public_router_id)
        LOG.info("project_network_cidr          %s" % self.project_network_cidr)
        LOG.info("[scenario]")
        LOG.info("img_dir                       %s" % self.img_dir)
        LOG.info("img_file                      %s" % self.img_file)
        LOG.info("img_disk_format               %s" % self.img_disk_format)
        LOG.info("img_container_format          %s" % self.img_container_format)
        LOG.info("ami_img_file                  %s" % self.ami_img_file)
        LOG.info("ari_img_file                  %s" % self.ari_img_file)
        LOG.info("aki_img_file                  %s" % self.aki_img_file)
        LOG.info("[validation]")
        LOG.info("image_ssh_user                %s" % self.image_ssh_user)
        LOG.info("image_ssh_password            %s" % self.image_ssh_password)
        LOG.info("[volume]")
        LOG.info("volume_size                   %s" % self.volume_size)


class ConfigHealthCheck(ConfigBase):
    def __init__(self, params):
        super(ConfigHealthCheck, self).__init__(params)
        self.params = params
        self.online_computes = self.params.get('online_computes')
        self.controller_nodes = self.params.get('controller_nodes')
        self.compute_nodes = self.params.get('compute_nodes')
        self.controller_node_ssh_user = \
            self.params.get('controller_node_ssh_user')
        self.controller_node_ssh_password = \
            self.params.get('controller_node_ssh_password')
        self.controller_node_ssh_key_path = \
            self.params.get('controller_node_ssh_key_path')
        self.project_network_cidr = self.params.get('project_network_cidr')
        self.tenant_network_mask_bits = \
            self.params.get('tenant_network_mask_bits')
        self.admin_horizonurl = self.params.get('admin_horizonurl')
        self.url = self.params.get('url')
        self.health_check_path = self.params.get('healthcheck_path')

    def prepare_conf_file(self, conf_path):
        raise NotImplementedError

    def gen_healthcheck_conf(self):
        """
        Generate healthcheck config
        """
        conf_path = self.health_check_path + '/etc/test.conf'
        self.prepare_conf_file(conf_path)

        # write /avocado-cloudtest/cloudtest/tests/healthcheck/
        # lenovo_rt_validation/fuel_health/etc/test.conf
        conf = ConfigParser.ConfigParser()
        conf.read(conf_path)
        conf.set("identity", "admin_horizonurl", self.admin_horizonurl)
        conf.set("identity", "uri", self.uri)
        conf.set("identity", "admin_username", self.admin_username)
        conf.set("identity", "admin_password", self.admin_password)
        conf.set("identity", "admin_tenant_name", self.admin_tenant_name)
        conf.set("compute", "online_computes", self.online_computes)
        conf.set("compute", "online_controllers", self.controller_nodes)
        conf.set("compute", "compute_nodes", self.compute_nodes)
        conf.set("compute", "controller_nodes", self.controller_nodes)
        conf.set("compute", "controller_node_ssh_user",
                 self.controller_node_ssh_user)
        conf.set("compute", "controller_node_ssh_password",
                 self.controller_node_ssh_password)
        conf.set("compute", "controller_node_ssh_key_path",
                 self.controller_node_ssh_key_path)
        conf.set("compute", "controller_node_ssh_key_path",
                 self.controller_node_ssh_key_path)
        conf.set("image", "http_image", self.http_image)
        conf.set("network", "project_network_cidr",
                 self.project_network_cidr)
        conf.set("network", "tenant_network_mask_bits",
                 self.tenant_network_mask_bits)

        self.save_conf_file(conf_path, conf,
                        "Write health check test.conf Error!",
                        "Failed to get content of test.conf for health check!")


class ConfigStability(ConfigBase):
    def __init__(self, params):
        super(ConfigStability, self).__init__(params)
        self.params = params
        self.netobj = Network(params)
        self.imgobj = Image(params)
        keyste = Keystone(params)
        self.tenant = keyste.get_tenant(params["OS_TENANT_NAME"])

    def create_secgroup_for_stability(self, name):
        secg = self.netobj.get_secgroup(name)
        if secg is None:
            LOG.info("Create security group for stability")
            result = self.netobj.create_secgroup(name=name)
            secgroup_id = result["security_group"]["id"]
            result = self.netobj.create_secgroup_rule_icmp(secgroup_id)
            result = self.netobj.create_secgroup_rule_ssh(secgroup_id)
            result = self.netobj.create_secgroup_rule_http(secgroup_id)
            result = self.netobj.create_secgroup_rule_mysql(secgroup_id)

    def create_net_topology_for_stability(self, net_name, router_name,
                                          start_cidr):
        net = self.netobj.get_network(net_name)
        rur = self.netobj.get_router(router_name, self.tenant.id)
        if net is None and rur is None:
            LOG.info("Create network topology for stability")
            self.netobj.create_network(name=net_name, subnet=True,
                                       start_cidr=start_cidr)
            self.netobj.create_router({"name" : router_name}, True)
            self.netobj.add_interface_router(net_name, router_name)

    def create_image_for_stability(self, name, image_path):
        img = self.imgobj.get_image(name)
        self.prepare_images_stability()
        if img is None:
            LOG.info("Create image for stability")
            self.imgobj.create_image(name, image_path)

    def prepare_images_stability(self):
        files = [self.params["image_ref_file"],
                 self.params["image_ref_alt_file"]]
        self.prepare_images(self.params["http_url"],
                            self.params["image_ref_dir"], files)

    def create_resources_for_stability(self, params):
        LOG.info("Start to prepare resource for stability...")
        self.create_net_topology_for_stability(
            params["stability_network_name"],
            params["stability_router_name"],
            params["stability_network_startcidr"])
        self.create_net_topology_for_stability(
            params["stability_network_alt_name"],
            params["stability_router_alt_name"],
            params["stability_network_alt_startcidr"])
        self.create_secgroup_for_stability(params["stability_secgroup_name"])
        self.create_image_for_stability(name=params["stability_image_name"],
                                        image_path=params["image_ref_path"])
        LOG.info("Prepare resource for stability done...")
