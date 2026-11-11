#!/usr/bin/env python3
"""Render k8s/pxc/cr.yaml from the operator's own default cr.yaml (same version),
with small-lab edits. Usage: render-cr.py <operator-version>   e.g. 1.20.0"""
import sys
import urllib.request

import yaml

version = sys.argv[1]
url = (
    "https://raw.githubusercontent.com/percona/percona-xtradb-cluster-operator/"
    f"v{version}/deploy/cr.yaml"
)
cr = yaml.safe_load(urllib.request.urlopen(url))
spec = cr["spec"]

# Small-lab resources (default requests are ~1 GB per pod, too much for one 8 GB host)
spec["pxc"]["resources"] = {
    "requests": {"memory": "600M", "cpu": "300m"},
    "limits": {"memory": "1G"},
}
# Spread the 3 members across the labeled zones (one member per zone)
spec["pxc"]["affinity"]["antiAffinityTopologyKey"] = "topology.kubernetes.io/zone"
spec["pxc"]["volumeSpec"]["persistentVolumeClaim"]["resources"]["requests"]["storage"] = "3G"
spec["haproxy"]["resources"] = {"requests": {"memory": "100M", "cpu": "100m"}}
spec["logcollector"]["enabled"] = False  # not needed for now

with open("k8s/pxc/cr.yaml", "w") as fh:
    yaml.safe_dump(cr, fh, sort_keys=False)
print(f"wrote k8s/pxc/cr.yaml (operator {version})")
