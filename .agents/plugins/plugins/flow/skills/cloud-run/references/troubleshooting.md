# Cloud Run Troubleshooting

## Container Fails to Start

```bash
# Check logs
gcloud run services logs read SERVICE --region=REGION

# Check revision status
gcloud run revisions describe REVISION --region=REGION
```

## High Latency

1. Check cold start frequency (enable min-instances)
2. Review concurrency settings
3. Check for CPU throttling
4. Profile application startup

## Memory Issues

1. Increase memory limit
2. Check for memory leaks
3. Reduce concurrency
4. Review in-memory caching

## Best Practices

### Security

1. **Use Workload Identity** instead of service account keys
2. **Store secrets in Secret Manager**
3. **Set appropriate ingress controls**
4. **Use VPC Connector for internal resources**
5. **Enable binary authorization** for trusted images only

### Reliability

1. **Set appropriate timeouts** for your workload
2. **Configure retries** for transient failures
3. **Use traffic splitting** for safe deployments
4. **Monitor with Cloud Monitoring** and set alerts

## Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [General Development Tips](https://cloud.google.com/run/docs/tips/general)
- [Cloud Run Samples](https://github.com/GoogleCloudPlatform/cloud-run-samples)
