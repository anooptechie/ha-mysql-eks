# Decisions

Record each project decision here with the reason.

## Local lab tooling (Phase 2)
- Host: Ubuntu EC2 t3.large; kubectl v1.37.2, kind v0.33.0
- Cluster: kind "ha-lab", 1 control-plane + 3 workers; workers labeled
  topology.kubernetes.io/zone=zone-a/b/c to practice zone spreading
- Limitation: kind has no real AZs and no EBS. Storage is node-local, so results
  here show operator behavior, not AZ/EBS behavior (that is tested on EKS).

## D1: MySQL operator
- Chosen: Percona Operator for MySQL based on Percona XtraDB Cluster (PXC)
- Why: longest track record of the three candidates, built-in S3 backups (Phase 5),
  Galera-style replication with automatic failover
- Considered: Percona Operator for MySQL (Percona Server based; newer, GA Nov 2025)
  and Oracle MySQL Operator (InnoDB Cluster + Router)
- Possible follow-up: repeat the Phase 4 chaos runs on a second operator to compare
- Risk: kind runs Kubernetes 1.37; documented operator support (June 2026) listed 1.33-1.36
## Observation: operator restarts (Phase 2)
- The operator pod restarted twice around the first cluster creation. Events show the
  kubelet killed it after its liveness probe (:8080/metrics) was refused three times, i.e.
  it had not started listening yet while the 2-vCPU host was busy pulling images and
  starting pods. No errors in the running log; restart count stable afterwards.
- kind runs Kubernetes 1.37, newer than the operator's documented range. If the operator
  misbehaves during Phase 4 chaos runs, recreate kind on a 1.36 node image and retest.
