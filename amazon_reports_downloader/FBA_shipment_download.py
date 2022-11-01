class FBAShipmentDownload(Object):
    def go_to_FBA_shipment_download_page(self):

        try:
            # 移动鼠标到reports
            for i in range(0, 3):
                click = 'false'
                try:
                    reports = WebDriverWait(self.driver, 940, 0.5).until(
                        EC.presence_of_element_located((By.ID, 'sc-navtab-reports')))
                    time.sleep(random.randint(4, 7))
                    webdriver.ActionChains(self.driver).move_to_element(reports).perform()
                    logger.info('go to reports')
                    js_change_display = 'document.querySelector("#sc-navtab-reports > ul").style.display = "block";'
                    js_change_opacity = 'document.querySelector("#sc-navtab-reports > ul").style.opacity = 1;'
                    self.driver.execute_script(js_change_display)
                    self.driver.execute_script(js_change_opacity)
                    # click fulfillments
                    try:
                        logger.info('click fulfillments')
                        fulfillment_link = self.driver.find_element_by_xpath(
                            '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Fulfil")]').get_attribute('href')
                        self.driver.get(fulfillment_link)
                        break
                    except Exception as e:
                        print(e)

                    # length = len(self.driver.find_elements_by_xpath('//*[@id="sc-navtab-reports"]/ul/li'))
                    # logger.info(length)
                    # for i in range(1, length):
                    #     logger.info(('//*[@id="sc-navtab-reports"]/ul/li[{}]'.format(i)))
                    #     report_name = self.driver.find_element_by_xpath(
                    #         '//*[@id="sc-navtab-reports"]/ul/li[{}]'.format(i)).text.strip()
                    #     if report_name.startswith('Fulfil'):
                    #         time.sleep(random.randint(7, 9))
                    #         js_click_fulfillments = "document.querySelector('#sc-navtab-reports > ul > li:nth-child({}) > a').click();".format(
                    #             i)
                    #         self.driver.execute_script(js_click_fulfillments)
                    #         logger.info('click fulfillments')
                    #         time.sleep(random.randint(1, 7))
                    #         click = 'true'
                    #         break
                    # if click == 'true':
                    #     break
                except Exception as e:
                    print(e)

            # click Amazon Fulfilled Shipments
            WebDriverWait(self.driver, 140, 0.5).until(EC.presence_of_element_located((By.ID, 'AFNShipmentReport')))
            afs_button_click = "document.querySelector('#AFNShipmentReport').click();"
            self.driver.execute_script(afs_button_click)


            logger.info('click Amazon Fulfilled Shipments')
            time.sleep(random.randint(1, 7))

            # click event date drop down choose date range
            # time.sleep(random.randint(20, 40))
            WebDriverWait(self.driver, 140, 0.5).until(EC.presence_of_element_located((By.ID, 'downloadDateDropdown'))).click()
            pt = '#downloadDateDropdown > option:nth-child({})'.format(random.randint(3, 5))
            logger.info(pt)
            WebDriverWait(self.driver, 20, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, pt))).click()
            # date_click = "document.querySelector('#downloadDateDropdown').value = {}".format(random.randint(3, 5))
            # logger.info(date_click)
            # self.driver.execute_script(date_click)

            logger.info('date range')
            time.sleep(random.randint(1, 7))

            # click  Request .txt Download

            # WebDriverWait(self.driver, 960, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#requestCsvTsvDownload tr:nth-child(1) button')))
            download_request_click = "javascript:FBAReporting.requestDownloadSubmitWithReportFileFormat('TSV');"
            self.driver.execute_script(download_request_click)

            logger.info('click  Request .txt Download')
            time.sleep(random.randint(1, 7))
            # click download

            download_button = WebDriverWait(self.driver, 900, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#downloadArchive table tbody tr:first-child a')))

            logger.info('downloading')
            time.sleep(random.randint(20, 50))

            download_link = download_button.get_attribute("href")
            logger.info(download_link)
            self.driver.get(download_link)
            FBA_shippment_name = re.findall(r"GET_AMAZON_FULFILLED_SHIPMENTS_DATA__(\d*)\.txt", download_link)[0]
            logger.info(FBA_shippment_name)
            return FBA_shippment_name + '.txt'

        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)
            self.driver.quit()