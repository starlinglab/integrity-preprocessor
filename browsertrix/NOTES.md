# NOTES

- [x] Update last checked time for each good crawl
- [x] Keep retrying the same crawl if something fails, infinitely
  - Log attempt number
- [x] Retry logic for HTTP requests
- [x] Stop using `r.ok`
- [ ] Wrapper func around requests to handle JWT expiry
- [ ] What is desired for metrics?
  - When to send
  - How to send
  - What fields
  - Should zero/empty fields still be sent
- [ ] Error count in metrics