"""
This module contains the publishers package.

The publishers package provides various classes for publishing data to different platforms, including FTP, SFTP, email,
Twitter, and WordPress.

Classes:
- base_publisher: The base class for all publishers.
- ftp_publisher: A publisher for FTP.
- sftp_publisher: A publisher for SFTP.
- email_publisher: A publisher for email.
- mastodon_publisher: A publisher for Mastodon.
- twitter_publisher: A publisher for Twitter.
- wordpress_publisher: A publisher for WordPress.
"""

__all__ = [
    "base_publisher",
    "ftp_publisher",
    "sftp_publisher",
    "email_publisher",
    "mastodon_publisher",
    "twitter_publisher",
    "wordpress_publisher",
]
