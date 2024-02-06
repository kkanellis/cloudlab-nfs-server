
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

# Number of NFS clients (there is always a server)
#pc.defineParameter("clientCount", "Number of NFS clients",
#                   portal.ParameterType.INTEGER, 2)

# Optional physical type for all nodes.
pc.defineParameter("phystype", "Optional physical node type",
                   portal.ParameterType.STRING, "c220g5",
                   longDescription="Specify a single physical node type (pc3000,d710,etc) " +
                   "instead of letting the resource mapper choose for you.")

pc.defineParameter("dataset", "Your dataset URN",
                   portal.ParameterType.STRING,
                   'urn:publicid:IDN+wisc.cloudlab.us:uw-mad-dash-pg0+ltdataset+tiering')

# Shared VLAN params
pc.defineParameter(
    "sharedVlanName","Name",
    portal.ParameterType.STRING,"kkanellis-nfs-tiering",
    longDescription="A shared VLAN name (functions as a private key allowing other experiments to connect to this node/VLAN). Must be fewer than 32 alphanumeric characters."),

pc.defineParameter(
    "sharedVlanAddress","Shared VLAN IP Address",
    portal.ParameterType.STRING,"10.254.254.1",
    longDescription="Set the IP address for the shared VLAN interface.  Make sure to use an unused address within the subnet of an existing shared vlan!"),

pc.defineParameter(
    "sharedVlanNetmask","Shared VLAN Netmask",
    portal.ParameterType.STRING,"255.255.255.0",
    longDescription="Set the subnet mask for the shared VLAN interface, as a dotted quad.")


# Always need this when using parameters
params = pc.bindParameters()

if params.phystype != "":
    tokens = params.phystype.split(",")
    if len(tokens) != 1:
        pc.reportError(portal.ParameterError("Only a single type is allowed", ["phystype"]))

pc.verifyParameters()

# The NFS network. All these options are required.
nfsLan = request.LAN(nfsLanName)
nfsLan.best_effort = True
nfsLan.vlan_tagging = True
nfsLan.link_multiplexing = True

# The NFS server.
nfsServer = request.RawPC(nfsServerName)
nfsServer.hardware_type = params.phystype
nfsServer.disk_image = params.osImage

# Attach server to lan.
nfsIface = nfsServer.addInterface()
nfsIface.addAddress(
    pg.IPv4Address(params.sharedVlanAddress, params.sharedVlanNetmask))
nfsLan.addInterface(nfsIface)

# Initialization script for the server
nfsServer.addService(pg.Execute(
    shell="sh", command="sudo /bin/bash /local/repository/nfs-server.sh"))

# Special node that represents the ISCSI device where the dataset resides
dsnode = request.RemoteBlockstore("dsnode", nfsDirectory)
dsnode.dataset = params.dataset
dsnode.readonly = False  # always mount the dataset as read-write

# Link between the nfsServer and the ISCSI device that holds the dataset
dslink = request.Link("dslink")
dsIface = nfsServer.addInterface()
dslink.addInterface(dsIface)
dslink.addInterface(dsnode.interface)
# Special attributes for this link that we must use.
dslink.best_effort = True
dslink.vlan_tagging = True
dslink.link_multiplexing = True

#vlanIface = nfsServer.addInterface("vlan1")
#vlanIface.addAddress(
#    pg.IPv4Address(params.sharedVlanAddress, params.sharedVlanNetmask))

# Attach server to shared vlan.
vlan = request.Link("vlan")
vlan.addInterface(nfsIface)
vlan.createSharedVlan(params.sharedVlanName)

vlan.link_multiplexing = True
vlan.best_effort = True

# The NFS clients, also attached to the NFS lan.
#for i in range(1, params.clientCount+1):
#    node = request.RawPC("node%d" % i)
#    node.disk_image = params.osImage
#    nfsLan.addInterface(node.addInterface())
#    # Initialization script for the clients
#    node.addService(pg.Execute(shell="sh", command="sudo /bin/bash /local/repository/nfs-client.sh"))
#    pass

# Print the RSpec to the enclosing page.
pc.printRequestRSpec(request)
