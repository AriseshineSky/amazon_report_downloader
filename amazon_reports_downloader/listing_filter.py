import os
import io
import re
import csv

from amazon_reports_downloader import logger


class ListingFilter():
    def get_headers(self, listing_report_path):
        headers = []
        with io.open(listing_report_path, encoding='utf-8-sig', errors='ignore') as fh:
            reader = csv.reader(fh, delimiter='\t')
            headers = next(reader)

        return headers

    def load_listings(self, listing_report_path):
        listing_report_path = os.path.abspath(os.path.expanduser(listing_report_path))
        if not os.path.isfile(listing_report_path):
            return

        with io.open(listing_report_path, encoding='utf-8-sig', errors='ignore') as fh:
            reader = csv.reader(fh, delimiter='\t')
            headers = next(reader)

            for line in reader:
                record = dict()
                for idx, header in enumerate(headers):
                    record[header] = line[idx]

                yield record

    def filter_listing_report(self, listing_report_path, output_path):
        headers = self.get_headers(listing_report_path)

        filtered_listings = ['\t'.join(headers)]
        for listing in self.load_listings(listing_report_path):
            if 'seller-sku' not in listing:
                logger.warning('[ListingMissingSku] %s', str(listing))
                continue

            sku = listing['seller-sku']
            if self.is_ds_listing(sku):
                continue

            values = []
            for header in headers:
                values.append(listing.get(header, ''))
            filtered_listings.append('\t'.join(values))

        if not filtered_listings:
            return

        output_dir = os.path.dirname(output_path)
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        with io.open(output_path, 'w+', encoding='utf-8') as fh:
            fh.write('\n'.join(filtered_listings))

    def is_ds_listing(self, sku):
        product_codes = ['b', 'c', 'g', 'p']
        condition_codes = ['p', 'b', 'n', 'x', 'm', 'g', 'u', 'j'];
        condition_patterns = ['new', 'xin', 'mint', 'brand_new'];
        formated_sku = sku.lower().replace('_', '-')

        # All DS Skus have '-' or '_'
        if formated_sku.find('-') == -1:
            return False

        # PL skus don't have word "book"
        if formated_sku.find('book') != -1:
            return True

        serial_number = formated_sku[-5:]
        serial_number_found = re.match(r'[0-9]{5}', serial_number) is not None

        sku_parts = formated_sku.split('-')
        last_part = sku_parts[-1]
        product_code = last_part[0]
        product_code_found = product_code in product_codes

        condition_code = formated_sku[0]
        condition_matched = False
        for condition_pattern in condition_patterns:
            if formated_sku.find(condition_pattern) != -1:
                condition_matched = True
                break

        condition_found = (condition_code in condition_codes) or condition_matched

        return condition_found and product_code_found and serial_number_found
