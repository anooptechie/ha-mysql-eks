# Decisions

Record each project decision here with the reason.

## Local lab tooling (Phase 2)
- Host: Ubuntu EC2 t3.large; kubectl v1.37.2, kind v0.33.0
- Cluster: kind "ha-lab", 1 control-plane + 3 workers; workers labeled
  topology.kubernetes.io/zone=zone-a/b/c to practice zone spreading
- Limitation: kind has no real AZs and no EBS. Storage is node-local, so results
  here show operator behavior, not AZ/EBS behavior (that is tested on EKS).
