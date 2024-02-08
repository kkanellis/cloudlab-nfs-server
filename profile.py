"""
NFS server that mounts and serves a remote dataset to other experiments,
using a shared VLAN (created by this experiment).
"""

import ipaddress

import geni.portal as portal
import geni.rspec.pg as pg
import geni.rspec.emulab as emulab

# Create a portal context.
pc = portal.Context()

# Create a Request object to start building the RSpec.
request = pc.makeRequestRSpec()

# Only Ubuntu images supported.
imageList = [
    ('urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU22-64-STD', 'UBUNTU 22.04'),
    ('urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU20-64-STD', 'UBUNTU 20.04'),
]

# Do not change these unless you change the setup scripts too.
nfsServerName = "nfs"
nfsLanName    = "nfsLan"
nfsDirectory  = "/nfs"

pc.defineParameter("osImage", "Select OS image",
                   portal.ParameterType.IMAGE,
                   imageList[0], imageList)

# Optional physical type for all nodes.
pc.defineParameter("phystype", "Optional physical node type",
    portal.ParameterType.STRING, "",
    longDescription="Specify a single physical node type (pc3000,d710,etc) " +
                    "instead of letting the resource mapper choose for you.")

pc.defineParameter("dataset", "Your dataset URN",
    portal.ParameterType.STRING,
    'urn:publicid:IDN+wisc.cloudlab.us:uw-mad-dash-pg0+ltdataset+ml-tiering')

# Shared VLAN params
pc.defineParameter("sharedVlanName","Shared VLAN Name",
    portal.ParameterType.STRING,"kkanellis-nfs-tiering",
    advanced=True,
    longDescription="A shared VLAN name (functions as a private key allowing other experiments to connect to this node/VLAN)."
                    "Must be fewer than 32 alphanumeric characters.")

pc.defineParameter("sharedVlanNetwork", "Shared VLAN Network",
    portal.ParameterType.STRING, "10.254.254.0/24",
    advanced=True,
    longDescription="Set the shared VLAN network, as a CIDR.")


# Always need this when using parameters
params = pc.bindParameters()

if params.phystype != "":
    tokens = params.phystype.split(",")
    if len(tokens) != 1:
        pc.reportError(portal.ParameterError("Only a single type is allowed", ["phystype"]))

pc.verifyParameters()

# Represent given network
network = ipaddress.IPv4Network(unicode(params.sharedVlanNetwork))
netmask = network.netmask
hosts = network.hosts()
gateway = next(hosts)

nfsLan = request.LAN(nfsLanName)
# Uncomment if only *one* experimental port available
#nfsLan.best_effort = True
#nfsLan.vlan_tagging = True
#nfsLan.link_multiplexing = True

# The NFS server.
nfsServer = request.RawPC(nfsServerName)
nfsServer.hardware_type = params.phystype
nfsServer.disk_image = params.osImage

# Create & attach server to vlan.
nfsIface = nfsServer.addInterface()
nfsIface.addAddress(
    pg.IPv4Address(gateway.compressed, netmask.compressed))
nfsLan.addInterface(nfsIface)
nfsLan.createSharedVlan(params.sharedVlanName)

# Initialization script for the server
nfsServer.addService(pg.Execute(
    shell="sh", command="sudo /bin/bash /local/repository/nfs-server.sh"))

# Special node that represents the ISCSI device where the dataset resides
dsnode = request.RemoteBlockstore("dsnode", nfsDirectory)
dsnode.dataset = params.dataset
dsnode.readonly = False  # always mount the dataset as read-write

# Link between the nfsServer and the ISCSI device that holds the dataset
dsIface = nfsServer.addInterface()
dslink = request.Link("dslink")
dslink.addInterface(dsIface)
dslink.addInterface(dsnode.interface)
# Special attributes for this link that we must use.
dslink.best_effort = True
dslink.vlan_tagging = True
dslink.link_multiplexing = True

# Print the RSpec to the enclosing page.
pc.printRequestRSpec(request)

