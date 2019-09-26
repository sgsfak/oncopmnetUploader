#!/usr/bin/python
# 
# plugin for uploading data to OncoPMNet
#

import json
import os
import sys
from ion.plugin import *
import subprocess
import traceback
from django.utils.functional import cached_property

def printlog(msg):
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    sys.stderr.flush()

class oncopmnetUploader(IonPlugin):
    """
    This plugin automates the upload of BAM files to the 
    backend storage platform of the OncoPMNet
    """
    version = "1.0.0.0"
    author = "ssfak@ics.forth.gr"

    mc_command = "/usr/local/bin/mc"

    @cached_property
    def startplugin_json(self):
        return self.startplugin

    def launch(self, data=None):
        """This is the primary launch method for the plugin."""

        plugin_run = self.startplugin_json['runinfo']['plugin']
        plugin_conf = plugin_run['pluginconfig']
        project = self.startplugin_json['expmeta']['project']
        self.workdir = plugin_run['results_dir']
        self.plugin_dir = plugin_run['path']

        ## TODO: check that the plugin has been configured properly
        ## we need `upload_path`, `access_key`, `secret_key`, and
        ## `server_host`
        upload_folder = plugin_conf['upload_path'].strip()
        if upload_folder.endswith('/'):
            upload_folder = upload_folder[:-1]

        server_alias = "oncopmnet"

        with open('barcodes.json', 'r') as barcodes_handle:
            barcodes = json.load(barcodes_handle)

        # Specify server host configuration through an environment variable:
        # export MC_HOST_<alias>=https://<Access Key>:<Secret Key>@<YOUR-S3-ENDPOINT>

        env = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
        env["MC_HOST_"+server_alias] = "https://%s:%s@%s" % (
            plugin_conf['access_key'],
            plugin_conf['secret_key'],
            plugin_conf['server_host'])
        #printlog("Conf: " + json.dumps(env))

        self.upload_info = []
        first = True
        for barcode_name, barcode_values in barcodes.iteritems():
            self.generate_completion_html(first and 'Started' or 'Running')
            first = False
            bam_file = barcode_values['bam_filepath']
            upload_path = "%s/%s/%s.bam" % (upload_folder, project, barcode_values['sample_id'])
            printlog("Sending %s to %s\n" % (bam_file, upload_path))
            p = subprocess.Popen([self.mc_command, "cp", bam_file, server_alias+"/"+upload_path], 
                cwd=self.workdir,
                env=env)
            exit_code = p.wait()
            exit_status = 'Failed'
            if exit_code == 0:
                exit_status = 'Succeeded'
            self.upload_info.append((os.path.basename(bam_file), upload_path, exit_status))
        self.generate_completion_html("Completed")
        # Exit the launch function; exit the plugin
        print("===============================================================================")
        return True

    def generate_completion_html(self, stat_line="Started", **kwargs):
        stat_fs_path = os.path.join(self.workdir, 'status_block.html')
        try:
            display_fs = open(stat_fs_path, "wb")
        except:
            print("Could not write status report")
            print(traceback.format_exc())
            raise

        _status_msg = """Progress is not available here.  
        Look for a message banner at the top of any webpage indicating that 
        the action was scheduled, or completed"""

        display_fs.write("<html><head>\n")
        # display_fs.write("<link href=\"/pluginMedia/IonCloud/bootstrap.min.css\" rel=\"stylesheet\">\n")
        display_fs.write("</head><body>\n")
        display_fs.write("<bold><h2>DATA UPLOAD</h2></bold>")
        # display_fs.write("<p>REPORT NAME: %s</p>" % (self.report_name))
        # display_fs.write("<p>REPORT ID: %s</p>" % (self.result_pk))
        display_fs.write("<ul>")
        for bam_file, upload_name, exit_status in self.upload_info:
            display_fs.write("<li>%s -> %s : <font color=\"red\">%s</font></li>" % (bam_file, upload_name, exit_status))
        display_fs.write("</ul>")
        if stat_line in ["Started", "Completed"]:
            display_fs.write("<p>STATUS: <font color=\"red\">%s</font></p>" % stat_line)
        else:
            display_fs.write("<p>STATUS: %s</p>" % stat_line)
            display_fs.write("<small>%s</small>" % _status_msg)
        for line in kwargs.get('error_msg', []):
            display_fs.write("%s<br>" % line)
        display_fs.write("<hr />")
        display_fs.write("<small>Contact: %s Version: %s</small>" % (self.author, self.version))
        display_fs.write("</body></html>\n")
        display_fs.close()

# Devel use - running directly
if __name__ == "__main__":
    PluginCLI()
