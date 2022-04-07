# NOTES

# TODO
- [x] Update last checked time for each good crawl
- [x] Keep retrying the same crawl if something fails, infinitely
  - Log attempt number
- [x] Retry logic for HTTP requests
- [x] Stop using `r.ok`
- [x] Wrapper func around requests to handle JWT expiry
- [x] Set up metrics
  - When to send
    - At the bottom of loop, or sooner, at end of crawl
  - How to send
    - Overwrite a file
  - What fields
    - Whatever I have
  - Should zero/empty fields still be sent
    - Yes
- [x] Error count in metrics
- [ ] When should `write_data` be called?

## Metrics format
Prometheus format.

- Basic: `cpu_temp 55`
- Complex: `node_cooling_device_max_state{name="1",type="Processor"} 3`
- Values inside `{}` must be strings, value at the end must be integer
