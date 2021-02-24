
# SSL Termination

If you would like to verify the SSL endpoint, you can run the following two commands and compare the fingerprint and serial no.

```
openssl s_client -showcerts -verify 5 -connect gwa.api.gov.bc.ca:443 -servername gwa.api.gov.bc.ca < /dev/null | awk '/BEGIN/,/END/{ if(/BEGIN/){a++}; print}' > gw.crt

openssl x509 -in gw.crt -fingerprint -serial -dates -noout
```

## *.api.gov.bc.ca

| Issue Date  | Expires     | Deployed    | SHA1 Fingerprint                                            | Serial No.                       |
|-------------|-------------|-------------|-------------------------------------------------------------|----------------------------------|
| Oct 6 2020  | Oct 16 2021 | Oct 6 2020  | 20:7D:15:9D:42:BE:CC:BC:FD:EF:DF:13:77:C7:25:A3:A4:72:45:05 | 7876EB597E14F728C8455504177D3BC9 |
| Feb 16 2021 | Oct 16 2021 | Feb 22 2021 | 4D:EA:CE:C4:0A:73:67:D3:B4:03:F6:63:C4:E1:67:2C:47:9D:EA:82 | 3B5849D8A670251A3C20EA7859BDF996 |

