#!/usr/bin/env bash
# __url_hash_filename, __url_cache_filename
# __cache_has_url, __cache_clear_url, __cache_purge
# cache_url, fetch_from_cache_to, fetch_and_expand

function __cache_location () {
    echo ${PRAXA_DOWNLOAD_CACHE}
}

function __url_hash_filename () {
    url="${1:?URL expected}"
    url_basename="$(basename ${url})"
    url_suffix="${2:-${url_basename##*.}}"
    hasher="${3:-$(which sha1deep)}"
    url_hash=$(echo $url | $hasher)
    echo "${url_hash}.${url_suffix,,}"
}

function __url_cache_filename () {
    url="${1:?URL expected}"
    cache_location="${2:-$(__cache_location)}"
    url_hash_filename="$(__url_hash_filename ${url})"
    cache_file="${cache_location}/${url_hash_filename}"
    echo $cache_file
}

function __cache_has_url () {
    url="${1:?URL expected}"
    cache_location="${2:-$(__cache_location)}"
    test -r $(__url_cache_filename ${url} ${cache_location})
}

function __cache_clear_url () {
    url="${1:?URL expected}"
    cache_location="${2:-$(__cache_location)}"
    rm $(__url_cache_filename $url $cache_location)
}

function __cache_purge () {
    cache_location="${1:-$(__cache_location)}"
    rm ${cache_location}/*
}

function cache_url () {
    url="${1:?URL expected}"
    cache_file="$(__url_cache_filename ${url})"
    __cache_has_url $url || download_to $url $cache_file 1>&2
    if [[ ! -r $cache_file ]]; then
        echo "- ERROR: no cached file: ${cache_file}" 1>&2
        echo ""
        return 1
    fi
    echo $cache_file
}

function hash_url () {
    url="${1:?URL expected}"
    hasher="${2:-$(which sha256deep) -zk}"
    cached_file="$(cache_url $url)"
    echo "+ Hashing content of URL: ${cached_file}"
    # echo "+ Using hasher: \`${hasher}\`"
    echo "> $($hasher $cached_file)"
}

function fetch_from_cache_to () {
    in_url="${1:?URL expected}"
    out_file="${2:?pathname expected}"
    [[ -r $out_file ]] && echo "- Already exists: ${out_file}" && return 1
    out_cached_file="$(cache_url $in_url)"
    echo "+ Fetching from cache: ${out_cached_file}"
    cp $out_cached_file $out_file
    [[ -r $out_file ]] && echo "+ Fetched from cache: ${out_file}"
}

function fetch_and_expand () {
    url="${1:?URL expected}"
    url_basename="$(basename ${url})"
    url_suffix="${url_basename##*.}"
    destination_directory="${2:-${url_basename%%.*}}"
    tmp_directory="$(__tmp_directory)"
    tmp_archive="${tmp_directory}/${url_basename}"
    fetch_from_cache_to $url $tmp_archive || return 1
    [[ ${url_suffix,,} == *zip ]] \
        && expand_zipwad_to $tmp_archive $destination_directory
    [[ ${url_suffix,,} != *zip ]] \
        && expand_tarball_to $tmp_archive $destination_directory
    rm $tmp_archive
    [[ -d $tmp_directory ]] && rm -rf $tmp_directory
}
