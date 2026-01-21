FROM mediawiki:1.37
ARG VER_MAJOR=1
ARG VER_MINOR=37
ARG VER_MINOR_BUMP=38

# Basic configuration
RUN echo "FallbackResource /index.php" > /etc/apache2/conf-enabled/99-mediawiki.conf

# Extension dependencies
RUN apt update
RUN apt install -y zip
COPY --from=composer:2.1 /usr/bin/composer /usr/bin/composer
COPY composer.local.json /var/www/html
RUN cd /var/www/html && composer require jumbojett/openid-connect-php:^"0.9.1" --ignore-platform-reqs

# Extensions
RUN git clone --depth 1 https://github.com/wikimedia/mediawiki-extensions-PluggableAuth /var/www/html/extensions/PluggableAuth -b REL${VER_MAJOR}_${VER_MINOR_BUMP}
RUN git clone --depth 1 https://github.com/wikimedia/mediawiki-extensions-OpenIDConnect /var/www/html/extensions/OpenIDConnect -b REL${VER_MAJOR}_${VER_MINOR_BUMP}
RUN git clone --depth 1 https://github.com/wikimedia/mediawiki-extensions-MobileFrontend /var/www/html/extensions/MobileFrontend -b REL${VER_MAJOR}_${VER_MINOR}
RUN git clone --depth 1 https://github.com/wikimedia/mediawiki-extensions-UserPageEditProtection /var/www/html/extensions/UserPageEditProtection -b REL${VER_MAJOR}_${VER_MINOR}
RUN git clone --depth 1 https://github.com/wikimedia/mediawiki-extensions-LastModified /var/www/html/extensions/LastModified -b REL${VER_MAJOR}_${VER_MINOR}

# Skins
RUN git clone --depth 1 https://github.com/smkent/metrolook /var/www/html/skins/Metrolook -b smkent_REL${VER_MAJOR}_${VER_MINOR}
