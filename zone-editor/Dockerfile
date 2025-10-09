ARG BUILD_FROM
FROM $BUILD_FROM
RUN apk --no-cache add nginx &&     mkdir -p /run/nginx /usr/share/nginx/html
COPY ingress.conf /etc/nginx/http.d/ingress.conf
COPY www/ /usr/share/nginx/html/
CMD ["nginx","-g","daemon off;error_log /dev/stdout debug;"]