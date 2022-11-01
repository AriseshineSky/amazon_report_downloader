class ListingDownload(object):
    def __init__(self, driver):
        self.driver = driver
    def go_to_listings_download_page(self):
        try:
            # 移动鼠标到inventory
            for i in range(0, 3):
                click = 'false'
                try:
                    inventory = WebDriverWait(self.driver, 40, 0.5).until(
                        EC.presence_of_element_located((By.ID, 'sc-navtab-inventory')))
                    time.sleep(random.randint(4, 7))
                    webdriver.ActionChains(self.driver).move_to_element(inventory).perform()

                    logger.info('go to inventory')
                    js_change_display = 'document.querySelector("#sc-navtab-inventory > ul").style.display = "block";'
                    js_change_opacity = 'document.querySelector("#sc-navtab-inventory > ul").style.opacity = 1;'
                    self.driver.execute_script(js_change_display)
                    self.driver.execute_script(js_change_opacity)
                    # click Inventory
                    try:
                        logger.info('click Inventory')
                        inventory_link = self.driver.find_element_by_xpath(
                            '//*[@id="sc-navtab-inventory"]/ul/li/a[contains(text(), "Inventory Reports")]').get_attribute(
                            'href')
                        self.driver.get(inventory_link)
                        break
                    except Exception as e:
                        print(e)

                    # length = len(self.driver.find_elements_by_xpath('//*[@id="sc-navtab-inventory"]/ul/li'))
                    # logger.info(length)
                    # for i in range(1, length):
                    #     report_name = self.driver.find_element_by_xpath(
                    #         '//*[@id="sc-navtab-inventory"]/ul/li[{}]'.format(i)).text.strip()
                    #     if report_name == 'Inventory Reports':
                    #         time.sleep(random.randint(7, 9))
                    #         js_click_inventory_reports = "document.querySelector('#sc-navtab-inventory > ul > li:nth-child({}) > a').click();".format(
                    #             i)
                    #         self.driver.execute_script(js_click_inventory_reports)
                    #         logger.info('click inventory reports')
                    #         time.sleep(random.randint(1, 7))
                    #         click = 'true'
                    #         break
                    # if click == 'true':
                    #     break
                except Exception as e:
                    print(e)

            # click Report Type drop down
            time.sleep(100)

            WebDriverWait(self.driver, 10, 0.5).until(
                EC.presence_of_element_located((By.ID, 'a-autoid-0-announce')))

            drop_down_js = 'document.querySelector("#a-autoid-0-announce").click();'
            self.driver.execute_script(drop_down_js)
            logger.info('click Report Type drop down')
            time.sleep(random.randint(4, 7))

            # click all listing report

            WebDriverWait(self.driver, 5, 0.5).until(
                EC.presence_of_element_located((By.ID, 'dropdown1_7')))
            all_listings_js = 'document.querySelector("#dropdown1_7").click();'
            self.driver.execute_script(all_listings_js)

            logger.info('click all listing report')
            time.sleep(random.randint(4, 7))

            # click request report button

            request_report_js = 'document.querySelector("#a-autoid-5 input").click();'
            self.driver.execute_script(request_report_js)

            logger.info('click request report button')
            time.sleep(random.randint(4, 7))

            self.driver.refresh()

            # download
            current_url = self.driver.current_url

            # 匹配“report_reference_id=”后面的数字
            pattern = re.compile(r'(?<=report_reference_id=)\d+\.?\d*')
            id = pattern.findall(current_url)[0]
            time.sleep(random.randint(1, 6))
            self.driver.refresh()
            for i in range(0, 3):
                try:
                    logger.info('%s-report_download' % id)
                    download_button = WebDriverWait(self.driver, 900, 0.5).until(EC.presence_of_element_located((By.ID, '%s-report_download' % id)))
                    download_report_js = '''document.querySelector("td[data-row='%s'] a").click();''' % id
                    self.driver.execute_script(download_report_js)
                    logger.info(download_button)
                    break
                except Exception as e:
                    print(e)
                    self.driver.quit()
            logger.info('All+Listings+Report+' + datetime.utcnow().date().strftime("%m-%d-%Y") + ".txt")
            time.sleep(random.randint(20, 50))
            return 'All+Listings+Report+' + datetime.utcnow().date().strftime("%m-%d-%Y") + ".txt"
        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)
            self.driver.quit()
    def close_tooltips(self):
        # close tooltips
        try:
            self.driver.find_element_by_xpath('//*[@id="step-0"]/div[2]/button').click()
        except:
            pass
