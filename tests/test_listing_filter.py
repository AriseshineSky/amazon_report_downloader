import os
import io
import csv

from amazon_reports_downloader.listing_filter import ListingFilter

import pytest


def test_is_ds_listing(listing_report_pathes, ds_skus, pl_skus):
    listing_filter = ListingFilter()
    for listing_report_path in listing_report_pathes:
        for listing in listing_filter.load_listings(listing_report_path):
            sku = listing['seller-sku']
            if listing_filter.is_ds_listing(sku):
                assert sku in ds_skus
            else:
                assert sku in pl_skus

def test_filter_listing_report(listing_report_pathes, pl_skus):
    listing_filter = ListingFilter()

    for listing_report_path in listing_report_pathes:
        output_filename = 'filtered_' + os.path.basename(listing_report_path)
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'tmp', output_filename)
        listing_filter.filter_listing_report(listing_report_path, output_path)

    for listing_report_path in listing_report_pathes:
        for listing in listing_filter.load_listings(output_path):
            assert listing['seller-sku'] in pl_skus
