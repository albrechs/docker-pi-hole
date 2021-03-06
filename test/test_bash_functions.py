import pytest
import re

# Override these docker command pieces to minimize parameter repititon
@pytest.fixture()
def cmd(request):
    return 'tail -f /dev/null'

@pytest.mark.parametrize('args,expected_ipv6,expected_stdout', [
    ('-e ServerIP="1.2.3.4"', True, 'IPv4 and IPv6'),
    ('-e ServerIP="1.2.3.4" -e "IPv6=True"', True, 'IPv4 and IPv6'),
    ('-e ServerIP="1.2.3.4" -e "IPv6=False"', False, 'IPv4'),
    ('-e ServerIP="1.2.3.4" -e "IPv6=foobar"', False, 'IPv4'),
])
def test_IPv6_not_True_removes_ipv6(Docker, tag, args, expected_ipv6, expected_stdout):
    ''' When a user overrides IPv6=True they only get IPv4 listening webservers '''
    IPV6_LINE = { 'alpine': 'listen \[::\]:80', 'debian': 'use-ipv6.pl' }
    WEB_CONFIG = { 'alpine': '/etc/nginx/nginx.conf', 'debian': '/etc/lighttpd/lighttpd.conf' }


    function = Docker.run('. /bash_functions.sh ; setup_ipv4_ipv6')
    assert "Using {}".format(expected_stdout) in function.stdout
    ipv6 = Docker.run('grep -q \'{}\' {}'.format(IPV6_LINE[tag], WEB_CONFIG[tag])).rc == 0
    assert ipv6 == expected_ipv6

@pytest.mark.parametrize('args, expected_stdout, dns1, dns2', [
    ('-e ServerIP="1.2.3.4"', 'default DNS', '8.8.8.8', '8.8.4.4' ),
    ('-e ServerIP="1.2.3.4" -e DNS1="1.2.3.4"', 'custom DNS', '1.2.3.4', '8.8.4.4' ),
    ('-e ServerIP="1.2.3.4" -e DNS2="1.2.3.4"', 'custom DNS', '8.8.8.8', '1.2.3.4' ),
    ('-e ServerIP="1.2.3.4" -e DNS1="1.2.3.4" -e DNS2="2.2.3.4"', 'custom DNS', '1.2.3.4', '2.2.3.4' ),
])
def test_DNS_Envs_override_defaults(Docker, args, expected_stdout, dns1, dns2):
    ''' When DNS environment vars are passed in, they override default dns servers '''
    function = Docker.run('. /bash_functions.sh ; eval `grep setup_dnsmasq_dns /start.sh`')
    assert expected_stdout in function.stdout

    docker_dns_servers = Docker.run('grep "^server=" /etc/dnsmasq.d/01-pihole.conf').stdout
    expected_servers = 'server={}\nserver={}\n'.format(dns1, dns2)
    assert expected_servers == docker_dns_servers

expected_debian_lines = [ 
    '"VIRTUAL_HOST" => "192.168.100.2"',
    '"ServerIP" => "192.168.100.2"',
    '"PHP_ERROR_LOG" => "/var/log/lighttpd/error.log"'
]
@pytest.mark.parametrize('tag,expected_lines,repeat_function', [
    ('debian', expected_debian_lines, 1),
    ('debian', expected_debian_lines, 2)
])
def test_debian_setup_php_env(Docker, tag, expected_lines, repeat_function):
    ''' confirm all expected output is there and nothing else '''
    stdout = ''
    for i in range(repeat_function):
        stdout = Docker.run('. /bash_functions.sh ; eval `grep setup_php_env /start.sh`').stdout
    for expected_line in expected_lines:
        search_config_cmd = "grep -c '{}' /etc/lighttpd/conf-enabled/15-fastcgi-php.conf".format(expected_line)
        search_config_count = Docker.run(search_config_cmd)
        assert search_config_count.stdout.rstrip('\n') == '1'
