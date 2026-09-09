#!/bin/sh
set -eu

script_directory=$(CDPATH= cd "$(dirname "$0")" && pwd)
default_jar="$script_directory/../imagej-service/target/imagej-service-1.0.0-SNAPSHOT.jar"
jar_path=${IMAGEJ_SERVICE_JAR:-$default_jar}
host=${IMAGEJ_SERVICE_HOST:-127.0.0.1}
port=${IMAGEJ_SERVICE_PORT:-8200}
max_heap=${IMAGEJ_SERVICE_MAX_HEAP:-768m}

if [ -z "${JAVA_HOME:-}" ]; then
  echo 'JAVA_HOME is required.' >&2
  exit 2
fi
java_executable=$JAVA_HOME/bin/java
if [ ! -x "$java_executable" ]; then
  echo 'JAVA_HOME/bin/java is not executable.' >&2
  exit 2
fi
case "${IMAGEJ_SERVICE_TOKEN:-}" in
  *[![:space:]]*) ;;
  *)
    echo 'IMAGEJ_SERVICE_TOKEN is required in the current process environment.' >&2
    exit 2
    ;;
esac
case "$host" in
  localhost|127.0.0.1|::1) ;;
  *)
    echo 'IMAGEJ_SERVICE_HOST must be a loopback address.' >&2
    exit 2
    ;;
esac
case "$port" in
  ''|*[!0-9]*|??????*)
    echo 'IMAGEJ_SERVICE_PORT must be an integer from 1 through 65535.' >&2
    exit 2
    ;;
esac
if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
  echo 'IMAGEJ_SERVICE_PORT must be an integer from 1 through 65535.' >&2
  exit 2
fi
if [ ! -f "$jar_path" ]; then
  echo 'The ImageJ service JAR does not exist.' >&2
  exit 2
fi

heap_unit=${max_heap#"${max_heap%?}"}
heap_value=${max_heap%?}
case "$heap_unit" in
  m|M|g|G) ;;
  *)
    echo 'IMAGEJ_SERVICE_MAX_HEAP must be a positive integer followed by m or g.' >&2
    exit 2
    ;;
esac
case "$heap_value" in
  ''|*[!0-9]*|0)
    echo 'IMAGEJ_SERVICE_MAX_HEAP must be a positive integer followed by m or g.' >&2
    exit 2
    ;;
esac

export IMAGEJ_SERVICE_HOST=$host
export IMAGEJ_SERVICE_PORT=$port

exec "$java_executable" "-Xmx$max_heap" -Djava.awt.headless=true -jar "$jar_path"
