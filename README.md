# requests-lb

A requests wrapper the implements discovery and load-balancing capabilities
through SRV records.

## Example

```python
req = RequestsLB('_web-service._http.example.com')
kw = dict(data="Hello World")
response = req.request('POST', 'hello/world', kw)
```

## lbcurl

A small utility called `lbcurl` is included in this package, which implements
a subset of curl switches to make it convenient to test requests using
requests-lb.

```bash
$ lbcurl http://_web-service._http.example.com/hello/world -d 'Hello World'
```
